from pathlib import Path

from services.qcontracts import MemoryRecord
from services.qlearning import (
    EvolutionStore,
    ProcedureStep,
    compose_candidate,
    evaluate_candidate,
    mine_candidates,
    policy_review,
    promote,
)
from services.qmemory2 import MemoryStore


def _remember_execution(store: MemoryStore, *, tool: str, outcome: str, idx: int, risk: str = "low") -> None:
    store.remember(MemoryRecord(
        namespace="user:default",
        kind="episodic",
        content={
            "key": f"execution:{tool}",
            "tool": tool,
            "arguments": {"path": f"/tmp/{idx}"},
            "capability": "files.write",
            "reversible": True,
            "risk": risk,
            "outcome": outcome,
            "stage": "complete" if outcome == "success" else "tool",
        },
        provenance={"type": "verified_receipt", "receipt_id": f"r{idx}"},
        confidence=0.98 if outcome == "success" else 0.72,
    ))


def test_mines_only_repeated_successful_verified_patterns(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite3")
    for i in range(4):
        _remember_execution(store, tool="files.write", outcome="success", idx=i)
    _remember_execution(store, tool="files.write", outcome="failure", idx=9)
    candidates = mine_candidates(store=store, min_samples=3, min_success_rate=0.75)
    store.close()

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.steps[0].tool == "files.write"
    assert candidate.steps[0].capability == "files.write"
    assert candidate.steps[0].reversible is True
    assert candidate.samples == 5
    assert candidate.success_rate == 0.8


def test_policy_review_never_grants_undeclared_authority() -> None:
    candidate = compose_candidate(
        "safe-copy", "copy learned from evidence",
        [ProcedureStep("files.copy", {"src": "a", "dst": "b"}, capability="files.write", reversible=True, risk="low")],
        evidence_memory_ids=["m1", "m2", "m3"], success_rate=1.0, samples=3,
    )
    ok, reason = policy_review(candidate, allowed_capabilities=[])
    assert ok is False
    assert reason == "undeclared_capability"

    ok, reason = policy_review(candidate, allowed_capabilities=["files.write"])
    assert ok is True
    assert reason == "policy_passed"


def test_high_risk_skill_requires_human_gate() -> None:
    candidate = compose_candidate(
        "system-change", "dangerous candidate",
        [ProcedureStep("system.change", {}, capability="system.admin", reversible=False, risk="high")],
        evidence_memory_ids=["m1"], success_rate=1.0, samples=3,
    )
    ok, reason = policy_review(candidate, allowed_capabilities=["system.admin"], max_auto_risk="low")
    assert ok is False
    assert reason == "risk_requires_human_approval"


def test_candidate_must_beat_baseline_and_not_regress(tmp_path: Path) -> None:
    candidate = compose_candidate(
        "fast-copy", "faster copy",
        [ProcedureStep("files.copy", {}, capability="files.write", reversible=True)],
        evidence_memory_ids=["m1", "m2", "m3"], success_rate=1.0, samples=3,
    )

    good = evaluate_candidate(candidate, baseline=lambda _: (0.70, 0), candidate_runner=lambda _: (0.92, 0))
    assert good.accepted is True
    assert good.improvement > 0

    bad = evaluate_candidate(candidate, baseline=lambda _: (0.70, 0), candidate_runner=lambda _: (0.95, 1))
    assert bad.accepted is False
    assert bad.reason == "regression_detected"

    evo = EvolutionStore(tmp_path / "evolution")
    receipt = promote(candidate, good, store=evo, allowed_capabilities=["files.write"])
    assert receipt.promoted is True
    assert Path(receipt.path).is_file()
    assert (tmp_path / "evolution" / "skills" / candidate.name / "ACTIVE").read_text() == receipt.version


def test_quantum_exploration_is_optional_and_proof_gated() -> None:
    candidate = compose_candidate(
        "route", "candidate search",
        [ProcedureStep("planner.route", {}, capability="planner", reversible=True)],
        evidence_memory_ids=["m1"] * 16, success_rate=1.0, samples=16,
    )

    def quantum_runner(payload):
        assert payload["candidate"]["name"] == "route"
        return {"ordering": [0]}, 0.96

    result = evaluate_candidate(
        candidate,
        baseline=lambda _: (0.70, 0),
        candidate_runner=lambda _: (0.90, 0),
        quantum_runner=quantum_runner,
        use_quantum=True,
    )
    assert result.accepted is True
    assert result.quantum_receipt is not None
    assert "accepted" in result.quantum_receipt
