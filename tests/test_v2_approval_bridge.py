import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qapproval_bridge", ROOT / "services" / "qapproval_bridge.py")
assert SPEC and SPEC.loader
qab = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qab
SPEC.loader.exec_module(qab)


class PlanState:
    plan = {
        "goal_id": "goal-1",
        "actions": [{
            "id": "action-1",
            "tool": "system.update",
            "capability": "system.modify",
            "risk": "high",
            "reversible": True,
            "arguments": {"package": "demo", "token": "secret-value"},
        }],
    }


def test_pending_is_derived_only_from_runtime_approval_event(tmp_path, monkeypatch):
    journal = tmp_path / "events.jsonl"
    rows = [
        {"topic": "receipt.created", "payload": {"id": "receipt-1", "evidence": {"runtime": {"simulation": {"verdict": "REQUIRE_APPROVAL"}}}}},
        {"topic": "approval.required", "payload": {"plan_id": "plan-1", "action_id": "action-1", "receipt_id": "receipt-1"}, "ts": 10.0},
    ]
    journal.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
    monkeypatch.setattr(qab, "DEFAULT_JOURNAL", journal)
    monkeypatch.setattr(qab, "load_plan", lambda _: PlanState())
    item = qab.pending()
    assert item["pending"] is True
    assert item["plan_id"] == "plan-1"
    assert item["action_id"] == "action-1"
    assert item["arguments"]["token"] == "<redacted>"


def test_decided_approval_is_not_reoffered(tmp_path, monkeypatch):
    journal = tmp_path / "events.jsonl"
    rows = [
        {"topic": "approval.required", "payload": {"plan_id": "plan-1", "action_id": "action-1", "receipt_id": "receipt-1"}, "ts": 10.0},
        {"topic": "approval.rejected", "payload": {"plan_id": "plan-1", "action_id": "action-1"}, "ts": 11.0},
    ]
    journal.write_text("\n".join(json.dumps(x) for x in rows), encoding="utf-8")
    monkeypatch.setattr(qab, "DEFAULT_JOURNAL", journal)
    monkeypatch.setattr(qab, "load_plan", lambda _: PlanState())
    assert qab.pending() == {"pending": False}


def test_approve_is_scoped_to_one_action(monkeypatch):
    monkeypatch.setattr(qab, "pending", lambda: {"pending": True, "plan_id": "plan-1", "action_id": "action-1", "goal_id": "goal-1"})
    monkeypatch.setattr(qab, "_record", lambda *args: None)
    calls = []
    def fake_execute(plan_id, *, approved=False, max_actions=None):
        calls.append((plan_id, approved, max_actions))
        return {"ok": False, "stage": "paused"} if len(calls) == 1 else {"ok": True, "stage": "done"}
    monkeypatch.setattr(qab, "execute_plan", fake_execute)
    out = qab.approve("plan-1", "action-1")
    assert out["ok"] is True
    assert calls[0] == ("plan-1", True, 1)
    assert calls[1] == ("plan-1", False, None)


def test_mismatched_action_cannot_be_approved(monkeypatch):
    monkeypatch.setattr(qab, "pending", lambda: {"pending": True, "plan_id": "plan-1", "action_id": "action-1"})
    assert qab.approve("plan-1", "action-other")["error"] == "approval-mismatch"


def test_shell_has_non_decorative_authorization_sheet():
    main = (ROOT / "shell" / "qml" / "Main.qml").read_text(encoding="utf-8")
    sheet = (ROOT / "shell" / "qml" / "components" / "AuthorizationSheet.qml").read_text(encoding="utf-8")
    cpp = (ROOT / "shell" / "src" / "AuthorizationBridge.cpp").read_text(encoding="utf-8")
    assert "authorizationBridge.pending" in main
    assert "authorizationSheet.open()" in main
    assert "authorizationBridge.approve()" in sheet
    assert "authorizationBridge.reject()" in sheet
    assert "Voir les changements" in sheet
    assert 'p->start(pythonExe(),{servicePath(),verb,plan,action})' in cpp
