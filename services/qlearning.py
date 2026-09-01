#!/usr/bin/env python3
"""Q-Learning / Q-Evolution for Quantic V2.

Verified experience is mined into *declarative* skill candidates composed only
of already-known tools. Candidates never gain authority by being generated:
they must beat a baseline, pass risk review, and are promoted as versioned
artifacts that can be rolled back. Optional quantum search may rank candidate
procedures, but the classical baseline remains authoritative until measured
advantage is proven by qquantum_broker.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable
import hashlib
import json
import os
import time
import uuid

try:
    from .qmemory2 import MemoryStore
    from .qquantum_broker import benchmark as quantum_benchmark, decide as quantum_decide, receipt_dict
except ImportError:
    from qmemory2 import MemoryStore
    from qquantum_broker import benchmark as quantum_benchmark, decide as quantum_decide, receipt_dict

DEFAULT_ROOT = Path(os.environ.get("QUANTIC_EVOLUTION_DIR", "/var/lib/quantic/evolution"))
RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj)).hexdigest()


@dataclass(frozen=True)
class ProcedureStep:
    tool: str
    arguments: dict[str, Any]
    capability: str = "unknown"
    reversible: bool = False
    risk: str = "low"


@dataclass(frozen=True)
class SkillCandidate:
    name: str
    description: str
    steps: list[ProcedureStep]
    evidence_memory_ids: list[str]
    success_rate: float
    samples: int
    source: str = "receipt_learning"
    id: str = field(default_factory=lambda: _id("candidate"))
    created_at: float = field(default_factory=time.time)

    @property
    def max_risk(self) -> str:
        return max((s.risk for s in self.steps), key=lambda x: RISK_ORDER.get(x, 99), default="low")


@dataclass(frozen=True)
class Evaluation:
    candidate_id: str
    accepted: bool
    candidate_score: float
    baseline_score: float
    improvement: float
    trials: int
    regressions: int
    reason: str
    quantum_receipt: dict[str, Any] | None = None


@dataclass(frozen=True)
class PromotionReceipt:
    candidate_id: str
    skill_name: str
    version: str
    digest: str
    path: str
    promoted: bool
    reason: str
    created_at: float = field(default_factory=time.time)


class EvolutionStore:
    def __init__(self, root: Path = DEFAULT_ROOT) -> None:
        self.root = Path(root)
        self.candidates = self.root / "candidates"
        self.skills = self.root / "skills"
        self.receipts = self.root / "receipts"

    @staticmethod
    def _atomic(path: Path, row: dict[str, Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        return path

    def save_candidate(self, candidate: SkillCandidate) -> Path:
        return self._atomic(self.candidates / f"{candidate.id}.json", asdict(candidate))

    def save_receipt(self, receipt: PromotionReceipt) -> Path:
        return self._atomic(self.receipts / f"{receipt.candidate_id}-{int(receipt.created_at)}.json", asdict(receipt))

    def list_versions(self, name: str) -> list[str]:
        root = self.skills / name
        if not root.exists():
            return []
        return sorted([p.name for p in root.iterdir() if p.is_dir()])

    def rollback(self, name: str, version: str) -> bool:
        target = self.skills / name / version
        if not target.is_dir():
            return False
        pointer = self.skills / name / "ACTIVE"
        pointer.parent.mkdir(parents=True, exist_ok=True)
        tmp = pointer.with_suffix(".tmp")
        tmp.write_text(version, encoding="utf-8")
        tmp.replace(pointer)
        return True


def mine_candidates(*, namespace: str = "user:default", store: MemoryStore | None = None,
                    min_samples: int = 3, min_success_rate: float = 0.80) -> list[SkillCandidate]:
    """Mine repeated verified execution patterns from episodic memory.

    The initial miner intentionally learns one-step skills only. Multi-step
    composition is handled separately so the system never invents ordering
    constraints that were not observed in evidence.
    """
    own = store is None
    store = store or MemoryStore()
    try:
        rows = store.export_namespace(namespace)
    finally:
        if own:
            store.close()
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("kind") != "episodic" or row.get("status") != "active":
            continue
        content = row.get("content", {})
        if not isinstance(content, dict) or not content.get("tool"):
            continue
        groups.setdefault(str(content["tool"]), []).append(row)

    out: list[SkillCandidate] = []
    for tool, items in groups.items():
        if len(items) < min_samples:
            continue
        successes = [x for x in items if x.get("content", {}).get("outcome") == "success"]
        rate = len(successes) / len(items)
        if rate < min_success_rate or not successes:
            continue
        # Prefer the most recent successful observed argument shape.
        exemplar = max(successes, key=lambda x: float(x.get("created_at", 0.0)))
        content = exemplar.get("content", {})
        step = ProcedureStep(
            tool=tool,
            arguments=dict(content.get("arguments", {})),
            capability=str(content.get("capability", "unknown")),
            reversible=bool(content.get("reversible", False)),
            risk=str(content.get("risk", "low")),
        )
        out.append(SkillCandidate(
            name=f"learned-{tool.replace('.', '-').replace('_', '-')}",
            description=f"Procedure learned from {len(items)} verified executions of {tool}",
            steps=[step],
            evidence_memory_ids=[str(x["id"]) for x in items],
            success_rate=rate,
            samples=len(items),
        ))
    return out


def compose_candidate(name: str, description: str, steps: Iterable[ProcedureStep], *,
                      evidence_memory_ids: Iterable[str], success_rate: float, samples: int) -> SkillCandidate:
    steps = list(steps)
    if not steps:
        raise ValueError("candidate requires at least one step")
    if not 0.0 <= success_rate <= 1.0:
        raise ValueError("success_rate must be between 0 and 1")
    return SkillCandidate(name, description, steps, list(evidence_memory_ids), success_rate, samples)


def policy_review(candidate: SkillCandidate, *, allowed_capabilities: Iterable[str] = (),
                  max_auto_risk: str = "low") -> tuple[bool, str]:
    allowed = set(allowed_capabilities)
    if any(step.capability != "unknown" and step.capability not in allowed for step in candidate.steps):
        return False, "undeclared_capability"
    if RISK_ORDER.get(candidate.max_risk, 99) > RISK_ORDER.get(max_auto_risk, -1):
        return False, "risk_requires_human_approval"
    if any(not step.tool or not isinstance(step.arguments, dict) for step in candidate.steps):
        return False, "invalid_step"
    return True, "policy_passed"


def evaluate_candidate(candidate: SkillCandidate, *,
                       baseline: Callable[[SkillCandidate], tuple[float, int]],
                       candidate_runner: Callable[[SkillCandidate], tuple[float, int]],
                       quantum_runner: Callable[[dict[str, Any]], tuple[Any, float]] | None = None,
                       use_quantum: bool = False) -> Evaluation:
    """Benchmark candidate against the current procedure.

    Runners return (score, regressions). A candidate must be at least as safe
    and strictly better in score. Quantum may be used only to select/rank a
    candidate representation; it cannot waive regression or policy gates.
    """
    b_score, b_reg = baseline(candidate)
    c_score, c_reg = candidate_runner(candidate)
    qreceipt = None
    if use_quantum:
        qd = quantum_decide("policy_exploration", backend_available=quantum_runner is not None,
                            estimated_size=max(16, len(candidate.steps) * max(candidate.samples, 1)))
        if qd.use_quantum and quantum_runner is not None:
            payload = {"candidate": asdict(candidate)}
            def classical(_: dict[str, Any]) -> tuple[Any, float]:
                return candidate, float(c_score)
            _, qr = quantum_benchmark("policy_exploration", payload, classical=classical,
                                      quantum=quantum_runner, higher_is_better=True)
            qreceipt = receipt_dict(qr)
    improvement = float(c_score) - float(b_score)
    accepted = c_reg <= b_reg and improvement > 0
    reason = "measured_improvement" if accepted else ("regression_detected" if c_reg > b_reg else "no_measured_improvement")
    return Evaluation(candidate.id, accepted, float(c_score), float(b_score), improvement,
                      max(candidate.samples, 1), int(c_reg), reason, qreceipt)


def promote(candidate: SkillCandidate, evaluation: Evaluation, *, store: EvolutionStore | None = None,
            allowed_capabilities: Iterable[str] = (), max_auto_risk: str = "low",
            version: str | None = None) -> PromotionReceipt:
    """Promote a declarative skill after evidence, benchmark and policy gates."""
    store = store or EvolutionStore()
    store.save_candidate(candidate)
    ok, reason = policy_review(candidate, allowed_capabilities=allowed_capabilities, max_auto_risk=max_auto_risk)
    if not evaluation.accepted:
        receipt = PromotionReceipt(candidate.id, candidate.name, version or "0", "", "", False, evaluation.reason)
        store.save_receipt(receipt)
        return receipt
    if not ok:
        receipt = PromotionReceipt(candidate.id, candidate.name, version or "0", "", "", False, reason)
        store.save_receipt(receipt)
        return receipt

    versions = store.list_versions(candidate.name)
    version = version or f"1.0.{len(versions)}"
    payload = {
        "schema": "quantic.skill.v2",
        "name": candidate.name,
        "version": version,
        "description": candidate.description,
        "source": candidate.source,
        "capabilities": sorted({s.capability for s in candidate.steps if s.capability != "unknown"}),
        "permissions": [],
        "steps": [asdict(s) for s in candidate.steps],
        "evidence_memory_ids": candidate.evidence_memory_ids,
        "evaluation": asdict(evaluation),
        "rollback_supported": True,
    }
    digest = _digest(payload)
    payload["sha256"] = digest
    root = store.skills / candidate.name / version
    path = store._atomic(root / "skill.json", payload)
    store.rollback(candidate.name, version)
    receipt = PromotionReceipt(candidate.id, candidate.name, version, digest, str(path), True, "promoted")
    store.save_receipt(receipt)
    return receipt
