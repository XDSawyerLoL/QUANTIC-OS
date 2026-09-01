from pathlib import Path

from services.qcontracts import Action, Goal, Intent, Mandate, MemoryRecord, Plan, Receipt, SkillManifest, to_dict
from services.qeventbus import EventBus


def test_contract_chain_has_stable_links():
    intent = Intent("Prepare the project")
    goal = Goal("Prepare project", intent.id, ["project verified"])
    action = Action("file.read", {"path": "/tmp/x"}, "file.read", reversible=True)
    plan = Plan(goal.id, [action])
    mandate = Mandate(goal.id, ["file.read"], max_actions=5)
    receipt = Receipt(action.id, goal.id, True, "complete", {"verified": True})

    assert goal.intent_id == intent.id
    assert plan.actions[0].id == action.id
    assert mandate.goal_id == goal.id
    assert receipt.goal_id == goal.id
    assert to_dict(receipt)["evidence"]["verified"] is True


def test_memory_and_skill_contracts_are_explicit():
    memory = MemoryRecord("project:test", "semantic", {"fact": "uses Quantic"}, {"source": "verified receipt"}, .95)
    skill = SkillManifest("inspect-project", "1.0.0", ["file.read"], ["read:project"], "skills/inspect.py", trusted=True)
    assert memory.confidence == .95
    assert skill.trusted is True
    assert skill.capabilities == ["file.read"]


def test_event_bus_persists_replays_and_dispatches(tmp_path: Path):
    journal = tmp_path / "events.jsonl"
    bus = EventBus(journal)
    seen = []
    bus.subscribe("goal.progress", seen.append)

    first = bus.emit("goal.progress", {"progress": 25}, "test", "goal_1")
    bus.emit("goal.progress", {"progress": 50}, "test", "goal_1")
    bus.emit("other", {"x": 1}, "test", "goal_2")

    assert seen[0].id == first.id
    replay = list(bus.replay(topic="goal.progress", correlation_id="goal_1"))
    assert [event.payload["progress"] for event in replay] == [25, 50]


def test_event_bus_skips_corrupt_journal_rows(tmp_path: Path):
    journal = tmp_path / "events.jsonl"
    journal.write_text("not-json\n", encoding="utf-8")
    bus = EventBus(journal)
    bus.emit("ok", {"value": 1}, "test")
    assert [event.topic for event in bus.replay()] == ["ok"]
