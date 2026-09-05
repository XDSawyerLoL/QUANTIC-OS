import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qnotification_bridge", ROOT / "services" / "qnotification_bridge.py")
assert SPEC and SPEC.loader
qnb = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qnb
SPEC.loader.exec_module(qnb)


def setup_paths(monkeypatch, tmp_path):
    journal = tmp_path / "events.jsonl"
    state = tmp_path / "notifications.json"
    monkeypatch.setenv("QUANTIC_EVENT_JOURNAL", str(journal))
    monkeypatch.setenv("QUANTIC_NOTIFICATION_STATE", str(state))
    return journal, state


def test_recent_projects_event_bus_rows(monkeypatch, tmp_path):
    journal, _ = setup_paths(monkeypatch, tmp_path)
    rows = [
        {"id":"evt1","topic":"agent.completed","payload":{"message":"Tâche terminée"},"source":"qagent","ts":100.0},
        {"id":"evt2","topic":"security.denied","payload":{"reason":"Action refusée"},"source":"qpolicy","ts":200.0},
    ]
    journal.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    result = qnb.recent(20)
    assert result["ok"] is True
    assert result["items"][0]["id"] == "evt2"
    assert result["items"][0]["severity"] == "critical"
    assert result["items"][1]["title"] == "Quantic"


def test_corrupt_rows_are_ignored(monkeypatch, tmp_path):
    journal, _ = setup_paths(monkeypatch, tmp_path)
    journal.write_text('{bad json}\n' + json.dumps({"id":"ok","topic":"health.ok","payload":{"status":"verified"},"source":"health","ts":1}), encoding="utf-8")
    result = qnb.recent()
    assert [item["id"] for item in result["items"]] == ["ok"]


def test_secrets_are_redacted(monkeypatch, tmp_path):
    journal, _ = setup_paths(monkeypatch, tmp_path)
    journal.write_text(json.dumps({"id":"evt","topic":"agent.output","payload":{"message":"token=supersecret done"},"source":"agent","ts":1}), encoding="utf-8")
    item = qnb.recent()["items"][0]
    assert "supersecret" not in item["message"]
    assert "[redacted]" in item["message"]


def test_clear_hides_older_events(monkeypatch, tmp_path):
    journal, _ = setup_paths(monkeypatch, tmp_path)
    journal.write_text(json.dumps({"id":"old","topic":"event","payload":{"message":"old"},"source":"q","ts":1}), encoding="utf-8")
    result = qnb.clear()
    assert result["ok"] is True
    assert qnb.recent()["items"] == []


def test_shell_notification_center_uses_live_bridge():
    main = (ROOT / "shell" / "src" / "main.cpp").read_text(encoding="utf-8")
    qml = (ROOT / "shell" / "qml" / "components" / "NotificationCenter.qml").read_text(encoding="utf-8")
    cmake = (ROOT / "shell" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert 'setContextProperty("notificationBridge"' in main
    assert "notificationBridge.items" in qml
    assert "notificationBridge.clearAll()" in qml
    assert "NotificationBridge.cpp" in cmake
