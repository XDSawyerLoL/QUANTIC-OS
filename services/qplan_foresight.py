#!/usr/bin/env python3
"""Q-Plan Foresight: predict fragile DAG nodes from verified experience.

The predictor is deliberately local and evidence based. It never claims certainty:
it estimates failure probability from historical verified episodic executions,
combines that with node risk and graph criticality, then can harden the DAG by
inserting explicit verification checkpoints *before* fragile work. Existing
authority is preserved; generated checkpoints request no new capabilities.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from typing import Any, Iterable
import math

try:
    from .qdag_runtime import DagNode, validate_dag, descendants
    from .qmemory2 import MemoryStore
    from .qquantum_broker import decide as quantum_decide
except ImportError:
    from qdag_runtime import DagNode, validate_dag, descendants
    from qmemory2 import MemoryStore
    from qquantum_broker import decide as quantum_decide

RISK_PRIOR = {"low": 0.06, "medium": 0.14, "high": 0.28, "critical": 0.45}


@dataclass(frozen=True)
class FailureStat:
    key: str
    samples: int
    failures: int
    failure_rate: float
    posterior_failure: float


@dataclass(frozen=True)
class NodeForecast:
    node_id: str
    key: str
    failure_probability: float
    samples: int
    criticality: float
    score: float
    fragile: bool
    reasons: list[str]


def _node_key(node: DagNode) -> str:
    task = node.task or {}
    return str(task.get("tool") or task.get("skill") or task.get("kind") or task.get("title") or node.id)


def learn_failure_stats(*, store: MemoryStore, namespace: str = "user:default", prior_strength: float = 4.0) -> dict[str, FailureStat]:
    """Learn tool/skill failure rates from active episodic receipt memories.

    Beta smoothing prevents a single failure from making a node look certain to
    fail. Only records that look like execution receipts are used.
    """
    rows = store.export_namespace(namespace)
    grouped: dict[str, list[bool]] = {}
    for row in rows:
        if row.get("kind") != "episodic" or row.get("status") != "active":
            continue
        content = row.get("content") or {}
        if not isinstance(content, dict):
            continue
        key = content.get("tool") or content.get("skill") or content.get("node_key")
        outcome = content.get("outcome")
        if not key or outcome not in {"success", "failure"}:
            continue
        grouped.setdefault(str(key), []).append(outcome == "failure")

    out: dict[str, FailureStat] = {}
    for key, vals in grouped.items():
        n = len(vals)
        f = sum(vals)
        empirical = f / n
        # Weak neutral prior around 10% failure; enough to regularize tiny samples.
        alpha = 0.10 * prior_strength
        beta = 0.90 * prior_strength
        posterior = (f + alpha) / (n + alpha + beta)
        out[key] = FailureStat(key, n, f, empirical, posterior)
    return out


def forecast_nodes(nodes: list[DagNode], *, stats: dict[str, FailureStat], fragility_threshold: float = 0.36) -> list[NodeForecast]:
    graph = validate_dag(nodes)
    total = max(1, len(nodes) - 1)
    forecasts: list[NodeForecast] = []
    for node in nodes:
        key = _node_key(node)
        stat = stats.get(key)
        prior = RISK_PRIOR.get(node.risk, 0.20)
        learned = stat.posterior_failure if stat else prior
        # Blend learned evidence with declared risk; more samples means more trust in history.
        evidence_weight = 0.0 if stat is None else min(0.82, math.log2(stat.samples + 1) / 6.0)
        probability = (1.0 - evidence_weight) * prior + evidence_weight * learned
        criticality = len(descendants(graph, [node.id])) / total
        score = 0.72 * probability + 0.28 * criticality
        reasons: list[str] = []
        if stat and stat.samples >= 3 and stat.failure_rate >= 0.25:
            reasons.append("historical_failures")
        if prior >= RISK_PRIOR["high"]:
            reasons.append("declared_risk")
        if criticality >= 0.50:
            reasons.append("high_downstream_impact")
        fragile = score >= fragility_threshold
        forecasts.append(NodeForecast(
            node.id, key, round(probability, 6), stat.samples if stat else 0,
            round(criticality, 6), round(score, 6), fragile, reasons,
        ))
    return sorted(forecasts, key=lambda x: x.score, reverse=True)


def harden_dag(nodes: list[DagNode], forecasts: Iterable[NodeForecast], *, max_checkpoints: int = 3) -> tuple[list[DagNode], dict[str, Any]]:
    """Insert capability-neutral preflight checkpoints before fragile nodes.

    Checkpoints inherit the fragile node's dependencies and the fragile node is
    rewired to depend on its checkpoint. The checkpoint itself requests no new
    capability and has low risk, so hardening cannot expand authority.
    """
    validate_dag(nodes)
    fragile = [f for f in forecasts if f.fragile][:max(0, max_checkpoints)]
    by_id = {n.id: n for n in nodes}
    chosen = [f for f in fragile if f.node_id in by_id]
    hardened = list(nodes)
    inserted: list[str] = []
    for f in chosen:
        target = by_id[f.node_id]
        checkpoint_id = f"preflight::{target.id}"
        if checkpoint_id in by_id:
            continue
        checkpoint = DagNode(
            id=checkpoint_id,
            task={
                "kind": "verification_checkpoint",
                "target_node": target.id,
                "predicted_failure_probability": f.failure_probability,
                "forecast_score": f.score,
                "reasons": list(f.reasons),
            },
            depends_on=list(target.depends_on),
            capabilities=[],
            risk="low",
        )
        hardened = [replace(n, depends_on=[checkpoint_id] if n.id == target.id else list(n.depends_on)) for n in hardened]
        hardened.append(checkpoint)
        by_id[checkpoint_id] = checkpoint
        inserted.append(checkpoint_id)
    validate_dag(hardened)
    return hardened, {"inserted_checkpoints": inserted, "hardened_nodes": [x.node_id for x in chosen]}


def advise_plan(nodes: list[DagNode], *, store: MemoryStore, namespace: str = "user:default",
                fragility_threshold: float = 0.36, checkpoint_budget: int = 3,
                quantum_backend_available: bool = False) -> dict[str, Any]:
    stats = learn_failure_stats(store=store, namespace=namespace)
    forecasts = forecast_nodes(nodes, stats=stats, fragility_threshold=fragility_threshold)
    hardened, change = harden_dag(nodes, forecasts, max_checkpoints=checkpoint_budget)
    # Quantum is only considered as a future optimizer for selecting checkpoints
    # when the combinatorial search is large; this decision never bypasses the
    # classical safety policy or changes authority.
    qdecision = quantum_decide(
        "policy_exploration",
        backend_available=quantum_backend_available,
        estimated_size=max(1, len(nodes) * max(1, checkpoint_budget)),
    )
    return {
        "forecasts": [asdict(x) for x in forecasts],
        "changes": change,
        "nodes": [asdict(x) for x in hardened],
        "quantum": asdict(qdecision),
    }
