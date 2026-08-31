#!/usr/bin/env python3
"""Q-Agent Runtime: policy + simulation + routing + Q-Twin + persistent task orchestration."""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import time

try:
    from .qpolicy import decide, audit
    from .qsimulation import evaluate, persist
    from .qtoolrouter import default_router
    from .qtwin import capture, state_diff, persist_snapshot
    from .qtasks import load as load_task, transition
except ImportError:
    from qpolicy import decide, audit
    from qsimulation import evaluate, persist
    from qtoolrouter import default_router
    from qtwin import capture, state_diff, persist_snapshot
    from qtasks import load as load_task, transition

RUNTIME_AUDIT = Path("/var/lib/quantic/audit/runtime.jsonl")


def _runtime_log(row: dict) -> None:
    try:
        RUNTIME_AUDIT.parent.mkdir(parents=True, exist_ok=True)
        with RUNTIME_AUDIT.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def execute(tool: str, arguments: dict, *, approved: bool = False, simulation_level: str = "SANDBOX") -> dict:
    router = default_router()
    spec = router.spec(tool)
    policy = decide(spec.capability, sandbox_available=True)
    audit(policy, {"tool": tool})

    if policy.verdict == "deny":
        out = {"ok": False, "stage": "policy", "decision": asdict(policy)}
        _runtime_log(out)
        return out

    sim = evaluate(spec.name, spec.category, spec.reversible, simulation_level)
    persist(sim)

    if sim.verdict in {"BLOCK", "REQUIRE_SIMULATION"}:
        out = {"ok": False, "stage": "simulation", "simulation": asdict(sim)}
        _runtime_log(out)
        return out

    needs_approval = policy.verdict == "approval" or sim.verdict == "REQUIRE_APPROVAL"
    if needs_approval and not approved:
        out = {"ok": False, "stage": "approval", "decision": asdict(policy), "simulation": asdict(sim)}
        _runtime_log(out)
        return out

    before = capture()
    try:
        persist_snapshot(before, "before")
    except OSError:
        pass

    try:
        result = router.invoke(tool, arguments)
        after = capture()
        try:
            persist_snapshot(after, "after")
        except OSError:
            pass
        verification = state_diff(before, after)
        out = {
            "ok": bool(result.get("ok", True)),
            "stage": "complete",
            "tool": tool,
            "result": result,
            "simulation": asdict(sim),
            "verification": verification,
        }
    except Exception as exc:
        out = {"ok": False, "stage": "tool", "tool": tool, "error": f"{type(exc).__name__}: {exc}", "simulation": asdict(sim)}
    _runtime_log(out)
    return out


def execute_task(task_id: str, *, approved: bool = False, simulation_level: str = "SANDBOX") -> dict:
    task = load_task(task_id)
    transition(task_id, "running")
    out = execute(task.tool, task.arguments, approved=approved, simulation_level=simulation_level)
    if out.get("stage") == "approval":
        transition(task_id, "waiting_approval")
    elif out.get("ok"):
        transition(task_id, "done")
    else:
        transition(task_id, "failed", out.get("error", out.get("stage", "unknown failure")))
    return out

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Quantic agent runtime")
    ap.add_argument("tool", nargs="?")
    ap.add_argument("arguments", nargs="?", default="{}")
    ap.add_argument("--task", default=None)
    ap.add_argument("--approved", action="store_true")
    ap.add_argument("--level", default="SANDBOX")
    ns = ap.parse_args()
    if ns.task:
        result = execute_task(ns.task, approved=ns.approved, simulation_level=ns.level)
    else:
        if not ns.tool:
            raise SystemExit("tool is required unless --task is used")
        result = execute(ns.tool, json.loads(ns.arguments), approved=ns.approved, simulation_level=ns.level)
    print(json.dumps(result, indent=2, ensure_ascii=False))
