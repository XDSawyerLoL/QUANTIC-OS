from pathlib import Path

from services.qcontracts import MemoryRecord, Receipt
from services.qmemory2 import MemoryStore
from services.qmemory_capture import capture_receipt
from services.qdream import consolidate
from services.qcontext import context_for_goal
from services.qmemory_trust import citation_lock, provenance_with_trust


def test_verified_receipts_consolidate_into_procedure(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    try:
        for i in range(2):
            receipt = Receipt(
                action_id=f"a{i}", goal_id="g1", ok=True, stage="complete",
                evidence={"runtime": {"verification": {"passed": True}}},
            )
            capture_receipt(receipt, tool="filesystem.read", arguments={"path": "/tmp/x"}, store=store)
        result = consolidate(namespace="goal:g1", store=store, diary=tmp_path / "dream.jsonl")
        assert result.promoted == 1
        recalled = store.recall("procedure filesystem read", namespace="goal:g1", kinds=["procedural"])
        assert recalled
        assert recalled[0]["provenance"]["type"] == "q-dream"
        assert len(recalled[0]["provenance"]["source_memory_ids"]) == 2
        assert citation_lock(recalled[0], for_action=True) is not None
    finally:
        store.close()


def test_context_is_bounded_and_keeps_provenance(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    try:
        for i in range(12):
            content = {"key": f"k{i}", "text": f"deploy project safely step {i}"}
            store.remember(MemoryRecord(
                namespace="user:default", kind="semantic",
                content=content,
                provenance=provenance_with_trust(
                    {"type": "test", "source": i}, content,
                    origin="user_explicit", source_id=f"test:context:{i}",
                ), confidence=0.9,
            ))
        goal = {"id": "goal-x", "title": "deploy project safely", "success_criteria": ["verified"]}
        ctx = context_for_goal(goal, store=store, limit=5)
        assert len(ctx["memories"]) == 5
        assert all("provenance" in item for item in ctx["memories"])
    finally:
        store.close()


def test_conflicting_outcomes_are_recorded_in_dream(tmp_path: Path):
    store = MemoryStore(tmp_path / "memory.sqlite3")
    try:
        for i, ok in enumerate((True, True, False)):
            receipt = Receipt(
                action_id=f"a{i}", goal_id="g2", ok=ok, stage="complete" if ok else "tool",
                evidence={"runtime": {"verification": {"passed": ok}}},
                error=None if ok else "boom",
            )
            capture_receipt(receipt, tool="browser.open", arguments={"url": "https://example.test"}, store=store)
        result = consolidate(namespace="goal:g2", store=store, diary=tmp_path / "dream.jsonl")
        assert result.promoted == 1
        assert result.conflicts == 1
    finally:
        store.close()
