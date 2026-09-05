from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from qconnectors import allowed
from qmcp_gateway import MCPServer, authorize
from qpolicy import decide
from qsimulation import evaluate
from qtoolrouter import default_router
from qtwin import compare
from qverify import verify
import qagent_runtime
import qagent
import qcompanion
import qcompanion_daemon
from qtwin import SystemSnapshot


def test_policy_fails_closed_for_unknown_capability():
    assert decide("unknown.capability").verdict == "deny"


def test_policy_blocks_protected_disk_boundary():
    assert decide("internal_disk.mount_rw").verdict == "deny"


def test_low_risk_read_simulation_is_allowed():
    sim = evaluate("file.read", "read", True, "SANDBOX")
    assert sim.verdict == "ALLOW"
    assert sim.risk == 0


def test_critical_irreversible_action_is_blocked():
    sim = evaluate("bootloader.write", "boot", False, "COMMIT")
    assert sim.verdict == "BLOCK"


def test_default_tools_are_read_only_capabilities():
    tools = {t["name"]: t for t in default_router().list_tools()}
    assert {"file.read", "file.search", "system.inspect"}.issubset(tools)
    assert all(tools[name]["category"] in {"read", "inspect"} for name in tools)


def test_unknown_connector_is_denied():
    ok, _ = allowed("missing", "file.read")
    assert ok is False


def test_untrusted_mcp_is_denied():
    server = MCPServer("demo", "stdio", "/bin/false", ["file.read"], False, False)
    assert authorize(server, "file.read")["ok"] is False


def test_network_mcp_requires_explicit_approval():
    server = MCPServer("remote", "https", "https://example.invalid/mcp", ["connector.read"], True, True)
    assert authorize(server, "connector.read", approved_network=False)["ok"] is False
    assert authorize(server, "connector.read", approved_network=True)["ok"] is True


def test_qtwin_rejects_regression():
    verdict = compare({"latency_ms": 100.0}, {"latency_ms": 120.0}, max_regression_pct=3.0)
    assert verdict.passed is False


def test_qtwin_accepts_improvement():
    verdict = compare({"tokens_per_second": 10.0}, {"tokens_per_second": 12.0}, max_regression_pct=3.0)
    assert verdict.passed is True


def test_qverify_rejects_failed_tool_result():
    verdict = verify("demo", {"ok": False})
    assert verdict.passed is False


def test_containment_source_has_no_shell_execution():
    src = (SERVICES / "qcontainment.py").read_text(encoding="utf-8")
    assert "shell=True" not in src
    assert "bubblewrap unavailable; fail closed" in src


def test_skills_require_integrity_digest():
    src = (SERVICES / "qskills.py").read_text(encoding="utf-8")
    assert "sha256" in src
    assert "expected == actual" in src


def test_runtime_wires_full_safety_chain_before_dispatch():
    src = (SERVICES / "qagent_runtime.py").read_text(encoding="utf-8")
    assert "decide(" in src
    assert "evaluate(" in src
    assert "capture()" in src
    assert "rollback_begin(" in src
    assert "verify(" in src
    assert "state_diff(" in src
    assert src.index("decide(") < src.index("router.invoke(")
    assert src.index("evaluate(") < src.index("router.invoke(")
    assert src.index("rollback_begin(") < src.index("router.invoke(")
    assert src.index("verify(") > src.index("router.invoke(")


def test_runtime_verifies_real_system_snapshots(monkeypatch):
    snapshots = [
        SystemSnapshot(1.0, "host", "kernel", "x86_64", "boot", 1000, 0.1, ["tmpfs /tmp rw"]),
        SystemSnapshot(2.0, "host", "kernel", "x86_64", "boot", 900, 0.2, ["tmpfs /tmp rw"]),
    ]
    monkeypatch.setattr(qagent_runtime, "capture", lambda: snapshots.pop(0))
    monkeypatch.setattr(qagent_runtime, "persist_snapshot", lambda *_: None)
    monkeypatch.setattr(qagent_runtime, "persist", lambda *_: None)
    monkeypatch.setattr(qagent_runtime, "audit", lambda *_: None)
    monkeypatch.setattr(qagent_runtime, "_runtime_log", lambda *_: None)
    monkeypatch.setattr(
        qagent_runtime,
        "rollback_begin",
        lambda *_: SimpleNamespace(id="rollback-test", reversible=True),
    )
    monkeypatch.setattr(qagent_runtime, "rollback_mark", lambda record, _state: record)

    result = qagent_runtime.execute("system.inspect", {})

    assert result["ok"] is True
    assert result["stage"] == "complete"
    assert result["verification"]["passed"] is True


def test_companion_persistence_uses_bound_state_tree(tmp_path, monkeypatch):
    status = tmp_path / "run" / "persistence.json"
    status.parent.mkdir(parents=True)
    status.write_text('{"mode":"persistent"}', encoding="utf-8")
    persistent_users = tmp_path / "var" / "lib" / "quantic" / "users"

    monkeypatch.delenv("QUANTIC_STATE", raising=False)
    monkeypatch.setattr(qcompanion_daemon, "PERSISTENCE_STATUS", status)
    monkeypatch.setattr(qcompanion_daemon, "PERSISTENT_USER_ROOT", persistent_users)
    monkeypatch.setattr(qcompanion.os, "getuid", lambda: 1234)

    state = qcompanion_daemon.choose_state()

    assert state == persistent_users / "1234"
    assert state.is_dir()
    assert state.stat().st_mode & 0o777 == 0o700
    unit = (ROOT / "systemd/user/quantic-companion.service").read_text(encoding="utf-8")
    assert "-/var/lib/quantic/users" in unit


def test_agent_reads_the_same_companion_memory_as_daemon(tmp_path, monkeypatch):
    state = tmp_path / "companion-state"
    memory = qcompanion_daemon.CompanionMemory(state / "companion.db")
    memory.remember("project:quantic", {"status": "persistent"})
    monkeypatch.setattr(qagent, "state_directory", lambda: state)

    context = qagent.companion_context()

    assert "project:quantic" in context
    assert "persistent" in context
