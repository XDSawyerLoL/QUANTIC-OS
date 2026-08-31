from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from qconnectors import allowed
from qpolicy import decide
from qsimulation import evaluate
from qtoolrouter import default_router
from qtwin import compare


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


def test_qtwin_rejects_regression():
    verdict = compare({"latency_ms": 100.0}, {"latency_ms": 120.0}, max_regression_pct=3.0)
    assert verdict.passed is False


def test_qtwin_accepts_improvement():
    verdict = compare({"tokens_per_second": 10.0}, {"tokens_per_second": 12.0}, max_regression_pct=3.0)
    assert verdict.passed is True


def test_containment_source_has_no_shell_execution():
    src = (SERVICES / "qcontainment.py").read_text(encoding="utf-8")
    assert "shell=True" not in src
    assert "bubblewrap unavailable; fail closed" in src


def test_runtime_wires_policy_simulation_and_twin_before_dispatch():
    src = (SERVICES / "qagent_runtime.py").read_text(encoding="utf-8")
    assert "decide(" in src
    assert "evaluate(" in src
    assert "capture()" in src
    assert "state_diff(" in src
    assert src.index("decide(") < src.index("router.invoke(")
    assert src.index("evaluate(") < src.index("router.invoke(")
