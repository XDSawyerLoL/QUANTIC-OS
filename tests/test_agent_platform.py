from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
sys.path.insert(0, str(SERVICES))

from qpolicy import decide
from qsimulation import evaluate
from qtoolrouter import default_router


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


def test_containment_source_has_no_shell_execution():
    src = (SERVICES / "qcontainment.py").read_text(encoding="utf-8")
    assert "shell=True" not in src
    assert "bubblewrap unavailable; fail closed" in src


def test_runtime_wires_policy_and_simulation_before_tool_dispatch():
    src = (SERVICES / "qagent_runtime.py").read_text(encoding="utf-8")
    assert "decide(" in src
    assert "evaluate(" in src
    assert src.index("decide(") < src.index("router.invoke(")
    assert src.index("evaluate(") < src.index("router.invoke(")
