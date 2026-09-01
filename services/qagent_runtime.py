#!/usr/bin/env python3
"""Q-Agent Runtime: policy + simulation + Q-Twin + verify + rollback + durable V2 plans."""
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
    from .qverify import verify
    from .qrollback import begin as rollback_begin, mark as rollback_mark, rollback
    from .qcontracts import Action, Goal, Plan, Receipt, to_dict
    from .qeventbus import EventBus
    from .qautonomy import save_goal, save_plan, load_goal, load_plan, update_goal, update_plan, resumable_goals
    from .qmemory_capture import capture_receipt
    from .qcontext import context_for_goal
except ImportError:
    from qpolicy import decide, audit
    from qsimulation import evaluate, persist
    from qtoolrouter import default_router
    from qtwin import capture, state_diff, persist_snapshot
    from qtasks import load as load_task, transition
    from qverify import verify
    from qrollback import begin as rollback_begin, mark as rollback_mark, rollback
    from qcontracts import Action, Goal, Plan, Receipt, to_dict
    from qeventbus import EventBus
    from qautonomy import save_goal, save_plan, load_goal, load_plan, update_goal, update_plan, resumable_goals
    from qmemory_capture import capture_receipt
    from qcontext import context_for_goal

RUNTIME_AUDIT = Path("/var/lib/quantic/audit/runtime.jsonl")
BUS = EventBus()
_SECRET_KEYS = {"password", "passwd", "secret", "token", "api_key", "apikey", "authorization", "cookie"}


def _runtime_log(row: dict) -> None:
    try:
        RUNTIME_AUDIT.parent.mkdir(parents=True, exist_ok=True)
        with RUNTIME_AUDIT.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _emit(topic: str, payload: dict, correlation_id: str | None = None) -> None:
    try:
        BUS.emit(topic, payload, "qagent_runtime", correlation_id)
    except OSError:
        pass


def _redact_arguments(value):
    if isinstance(value, dict):
        return {k: ("<redacted>" if str(k).lower() in _SECRET_KEYS else _redact_arguments(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_arguments(x) for x in value]
    return value


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
    try: persist_snapshot(before, "before")
    except OSError: pass

    journal = rollback_begin(tool, {"arguments": arguments, "before": before}, spec.reversible)
    try:
        result = router.invoke(tool, arguments)
        after = capture()
        try: persist_snapshot(after, "after")
        except OSError: pass
        twin_diff = state_diff(before, after)
        verification = verify(tool, result, before, after)

        if verification.passed:
            rollback_mark(journal, "committed")
            out = {
                "ok": bool(result.get("ok", True)), "stage": "complete", "tool": tool,
                "result": result, "simulation": asdict(sim), "twin": twin_diff,
                "verification": asdict(verification), "rollback_record": journal.id,
            }
        else:
            rb = rollback(journal)
            out = {
                "ok": False, "stage": "verify", "tool": tool, "result": result,
                "simulation": asdict(sim), "twin": twin_diff,
                "verification": asdict(verification), "rollback": rb,
            }
    except Exception as exc:
        rb = rollback(journal)
        out = {
            "ok": False, "stage": "tool", "tool": tool,
            "error": f"{type(exc).__name__}: {exc}", "simulation": asdict(sim),
            "rollback": rb,
        }
    _runtime_log(out)
    return out


def register_goal_plan(goal: Goal, plan: Plan) -> dict:
    """Persist a goal/plan pair and publish lifecycle + bounded memory context."""
    if plan.goal_id != goal.id:
        raise ValueError("plan.goal_id must match goal.id")
    save_goal(goal, active_plan_id=plan.id)
    save_plan(plan)
    _emit("goal.created", to_dict(goal), goal.id)
    memory_context = {"goal_id": goal.id, "memories": []}
    try:
        memory_context = context_for_goal(goal)
        _emit("memory.context.prepared", memory_context, goal.id)
    except (OSError, ValueError):
        pass
    _emit("plan.created", {**to_dict(plan), "memory_context": memory_context}, goal.id)
    return {"goal_id": goal.id, "plan_id": plan.id, "actions": len(plan.actions), "memory_context": memory_context}


def _action_from_row(row: dict) -> Action:
    return Action(**row)


def _remember(receipt: Receipt, action: Action) -> None:
    try:
        memory = capture_receipt(
            receipt,
            tool=action.tool,
            arguments=_redact_arguments(action.arguments),
            capability=action.capability,
            reversible=action.reversible,
            risk=action.risk,
        )
        _emit("memory.captured", {"memory_id": memory.id, "receipt_id": receipt.id, "kind": memory.kind}, receipt.goal_id)
    except (OSError, ValueError):
        pass


def execute_plan(plan_id: str, *, approved: bool = False, simulation_level: str = "SANDBOX", max_actions: int | None = None) -> dict:
    """Execute or resume a durable plan from its next unfinished action."""
    plan_state = load_plan(plan_id)
    plan = plan_state.plan
    goal_id = str(plan["goal_id"])
    goal_state = load_goal(goal_id)
    actions = [_action_from_row(x) for x in plan.get("actions", [])]

    start = int(plan_state.next_action)
    if start >= len(actions):
        update_plan(plan_id, state="done")
        update_goal(goal_id, state="done", current_action=len(actions))
        _emit("goal.completed", {"goal_id": goal_id, "plan_id": plan_id}, goal_id)
        return {"ok": True, "stage": "done", "goal_id": goal_id, "plan_id": plan_id, "completed": len(actions)}

    update_plan(plan_id, state="running")
    update_goal(goal_id, state="running", attempts=goal_state.attempts + 1, current_action=start)
    _emit("plan.started", {"plan_id": plan_id, "resume_from": start}, goal_id)

    executed = 0
    for index in range(start, len(actions)):
        if max_actions is not None and executed >= max_actions:
            update_plan(plan_id, state="paused", next_action=index)
            update_goal(goal_id, state="paused", current_action=index)
            _emit("plan.paused", {"plan_id": plan_id, "next_action": index, "reason": "action_budget"}, goal_id)
            return {"ok": False, "stage": "paused", "goal_id": goal_id, "plan_id": plan_id, "next_action": index}

        action = actions[index]
        _emit("action.started", {"plan_id": plan_id, "index": index, "action": to_dict(action)}, goal_id)
        out = execute(action.tool, action.arguments, approved=approved, simulation_level=simulation_level)
        receipt = Receipt(
            action_id=action.id,
            goal_id=goal_id,
            ok=bool(out.get("ok")),
            stage=str(out.get("stage", "unknown")),
            evidence={"runtime": out},
            error=out.get("error"),
        )
        _emit("receipt.created", to_dict(receipt), goal_id)
        _remember(receipt, action)

        if out.get("stage") == "approval":
            update_plan(plan_id, state="waiting_approval", next_action=index, last_receipt_id=receipt.id)
            update_goal(goal_id, state="waiting_approval", current_action=index)
            _emit("approval.required", {"plan_id": plan_id, "action_id": action.id, "receipt_id": receipt.id}, goal_id)
            return {"ok": False, "stage": "approval", "goal_id": goal_id, "plan_id": plan_id, "receipt": to_dict(receipt)}

        if not out.get("ok"):
            update_plan(plan_id, state="failed", next_action=index, last_receipt_id=receipt.id)
            update_goal(goal_id, state="failed", current_action=index, last_error=receipt.error or receipt.stage)
            _emit("action.failed", {"plan_id": plan_id, "index": index, "receipt": to_dict(receipt)}, goal_id)
            return {"ok": False, "stage": "failed", "goal_id": goal_id, "plan_id": plan_id, "receipt": to_dict(receipt)}

        completed = list(plan_state.completed_action_ids or [])
        if action.id not in completed:
            completed.append(action.id)
        plan_state = update_plan(
            plan_id,
            state="running",
            next_action=index + 1,
            completed_action_ids=completed,
            last_receipt_id=receipt.id,
        )
        update_goal(goal_id, state="running", current_action=index + 1)
        _emit("action.completed", {"plan_id": plan_id, "index": index, "receipt": to_dict(receipt)}, goal_id)
        executed += 1

    update_plan(plan_id, state="done", next_action=len(actions))
    update_goal(goal_id, state="done", current_action=len(actions))
    _emit("plan.completed", {"plan_id": plan_id, "actions": len(actions)}, goal_id)
    _emit("goal.completed", {"goal_id": goal_id, "plan_id": plan_id}, goal_id)
    return {"ok": True, "stage": "done", "goal_id": goal_id, "plan_id": plan_id, "completed": len(actions)}


def resume_pending(*, approved: bool = False, simulation_level: str = "SANDBOX") -> list[dict]:
    """Resume durable goals after restart, excluding approval-blocked work."""
    results: list[dict] = []
    for goal_state in resumable_goals():
        plan_id = goal_state.active_plan_id
        if not plan_id:
            continue
        _emit("goal.resuming", {"goal_id": goal_state.goal.get("id"), "plan_id": plan_id}, goal_state.goal.get("id"))
        results.append(execute_plan(plan_id, approved=approved, simulation_level=simulation_level))
    return results


def execute_task(task_id: str, *, approved: bool = False, simulation_level: str = "SANDBOX") -> dict:
    task = load_task(task_id)
    transition(task_id, "running")
    out = execute(task.tool, task.arguments, approved=approved, simulation_level=simulation_level)
    if out.get("stage") == "approval":
        transition(task_id, "waiting_approval")
    elif out.get("ok"):
        transition(task_id, "done")
    elif out.get("stage") == "verify" and out.get("rollback"):
        transition(task_id, "rolled_back", "verification failed; rollback requested")
    else:
        transition(task_id, "failed", out.get("error", out.get("stage", "unknown failure")))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Quantic agent runtime")
    ap.add_argument("tool", nargs="?")
    ap.add_argument("arguments", nargs="?", default="{}")
    ap.add_argument("--task", default=None)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--approved", action="store_true")
    ap.add_argument("--level", default="SANDBOX")
    ns = ap.parse_args()
    if ns.resume:
        result = resume_pending(approved=ns.approved, simulation_level=ns.level)
    elif ns.plan:
        result = execute_plan(ns.plan, approved=ns.approved, simulation_level=ns.level)
    elif ns.task:
        result = execute_task(ns.task, approved=ns.approved, simulation_level=ns.level)
    else:
        if not ns.tool:
            raise SystemExit("tool is required unless --task, --plan or --resume is used")
        result = execute(ns.tool, json.loads(ns.arguments), approved=ns.approved, simulation_level=ns.level)
    print(json.dumps(result, indent=2, ensure_ascii=False))
