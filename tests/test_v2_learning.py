from pathlib import Path
import json

from services import qskills
from services.qcontracts import MemoryRecord, Receipt
from services.qlearning import (
    EvolutionStore,
    ProcedureStep,
    compose_candidate,
    evaluate_candidate,
    mine_candidates,
    policy_review,
    promote,
)
from services.qmemory_capture import capture_receipt
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


def test_default_runtime_receipts_feed_learning_namespace(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.sqlite3")
    try:
        for i in range(3):
            receipt = Receipt(
                action_id=f"a{i}", goal_id=f"goal-{i}", ok=True, stage="complete",
                evidence={"runtime": {"verification": {"passed": True}}},
            )
            record = capture_receipt(
                receipt,
                tool="files.copy",
                arguments={"src": f"/tmp/{i}", "dst": "/tmp/out"},
                capability="files.write",
                reversible=True,
                store=store,
            )
            assert record.namespace == "user:default"
        candidates = mine_candidates(store=store, min_samples=3, min_success_rate=1.0)
        assert [candidate.name for candidate in candidates] == ["learned-files-copy"]
        assert candidates[0].samples == 3
    finally:
        store.close()


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


def test_candidate_must_beat_baseline_and_not_regress(tmp_path: Path, monkeypatch) -> None:
    candidate = compose_candidate(
        "fast-copy", "faster copy",
        [ProcedureStep("files.copy", {"token": "must-not-be-published"}, capability="files.write", reversible=True)],
        evidence_memory_ids=["m1", "m2", "m3"], success_rate=1.0, samples=3,
    )

    good = evaluate_candidate(candidate, baseline=lambda _: (0.70, 0), candidate_runner=lambda _: (0.92, 0))
    assert good.accepted is True
    assert good.improvement > 0

    bad = evaluate_candidate(candidate, baseline=lambda _: (0.70, 0), candidate_runner=lambda _: (0.95, 1))
    assert bad.accepted is False
    assert bad.reason == "regression_detected"

    skill_root = tmp_path / "skills"
    evo = EvolutionStore(tmp_path / "evolution", skill_root=skill_root)
    receipt = promote(candidate, good, store=evo, allowed_capabilities=["files.write"])
    assert receipt.promoted is True
    manifest_path = Path(receipt.path)
    assert manifest_path.is_file()
    assert (skill_root / candidate.name / "ACTIVE").read_text() == receipt.version
    manifest = json.loads(manifest_path.read_text())
    assert manifest["entrypoint"] == "procedure.json"
    assert manifest["tools"] == ["files.copy"]
    procedure = json.loads((manifest_path.parent / manifest["entrypoint"]).read_text())
    assert procedure["steps"][0]["arguments"]["token"] == "<redacted>"
    monkeypatch.setattr(qskills, "USER_ROOT", skill_root)
    loaded = qskills.load_manifest(manifest_path)
    assert loaded.trusted is True
    assert loaded.tools == ["files.copy"]
    discovered = {skill.name: skill for skill in qskills.discover()}
    assert discovered[candidate.name].trusted is True


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
