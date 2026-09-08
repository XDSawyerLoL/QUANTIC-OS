#!/usr/bin/env python3
"""Q-Quantum Broker: optional, proof-gated quantum acceleration for Quantic.

Quantum is never used as decoration. A backend is eligible only for a supported
problem class, and its result must be benchmarked against a classical baseline.
The classical path remains authoritative until measured advantage is proven.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Callable
import time

SUPPORTED = {"combinatorial_optimization", "robust_optimization", "sampling", "search", "policy_exploration"}

@dataclass(frozen=True)
class QuantumDecision:
    use_quantum: bool
    problem_class: str
    reason: str
    backend: str = "classical"
    require_baseline: bool = True

@dataclass(frozen=True)
class QuantumReceipt:
    problem_class: str
    backend: str
    accepted: bool
    quantum_ms: float | None
    classical_ms: float
    quantum_score: float | None
    classical_score: float
    advantage: float
    reason: str


def decide(problem_class: str, *, backend_available: bool, estimated_size: int = 0, min_size: int = 16) -> QuantumDecision:
    if problem_class not in SUPPORTED:
        return QuantumDecision(False, problem_class, "unsupported_problem_class")
    if not backend_available:
        return QuantumDecision(False, problem_class, "no_quantum_backend")
    if estimated_size and estimated_size < min_size:
        return QuantumDecision(False, problem_class, "classical_overhead_likely_lower")
    return QuantumDecision(True, problem_class, "eligible_for_quantum_trial", backend="quantum")


def benchmark(problem_class: str, payload: dict[str, Any], *, classical: Callable[[dict[str, Any]], tuple[Any, float]], quantum: Callable[[dict[str, Any]], tuple[Any, float]] | None = None, higher_is_better: bool = True) -> tuple[Any, QuantumReceipt]:
    t0=time.perf_counter(); c_result,c_score=classical(payload); c_ms=(time.perf_counter()-t0)*1000.0
    if quantum is None:
        return c_result, QuantumReceipt(problem_class,"classical",False,None,c_ms,None,float(c_score),0.0,"quantum_unavailable")
    try:
        t1=time.perf_counter(); q_result,q_score=quantum(payload); q_ms=(time.perf_counter()-t1)*1000.0
    except Exception as exc:
        return c_result, QuantumReceipt(problem_class,"classical",False,None,c_ms,None,float(c_score),0.0,f"quantum_error:{type(exc).__name__}")
    c=float(c_score); q=float(q_score)
    quality_gain=(q-c) if higher_is_better else (c-q)
    latency_gain=(c_ms-q_ms)/max(c_ms,1e-9)
    advantage=0.8*quality_gain+0.2*latency_gain
    accepted=quality_gain >= 0 and advantage > 0
    if accepted:
        return q_result, QuantumReceipt(problem_class,"quantum",True,q_ms,c_ms,q,c,advantage,"measured_advantage")
    return c_result, QuantumReceipt(problem_class,"classical",False,q_ms,c_ms,q,c,advantage,"classical_baseline_wins")


def receipt_dict(receipt: QuantumReceipt) -> dict[str, Any]:
    return asdict(receipt)
