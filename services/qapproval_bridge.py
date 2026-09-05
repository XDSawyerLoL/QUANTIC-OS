#!/usr/bin/env python3
"""Q-Approval Bridge: human authorization boundary for Quantic Desktop.

The shell never approves an arbitrary command. It can only accept/reject the exact
currently pending action emitted by qagent_runtime as ``approval.required``.
Approval is scoped to one action; subsequent plan work resumes without carrying
that approval token forward.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

try:
    from .qeventbus import EventBus, DEFAULT_JOURNAL
    from .qautonomy import load_plan, update_plan, update_goal
    from .qagent_runtime import execute_plan
except ImportError:
    from qeventbus import EventBus, DEFAULT_JOURNAL
    from qautonomy import load_plan, update_plan, update_goal
    from qagent_runtime import execute_plan

ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
DECISIONS = Path("/var/lib/quantic/approvals/decisions.jsonl")
BUS = EventBus()
_SECRET_KEYS = {"password", "passwd", "secret", "token", "api_key", "apikey", "authorization", "cookie"}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): ("<redacted>" if str(k).lower() in _SECRET_KEYS else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _events() -> list[dict[str, Any]]:
    path = DEFAULT_JOURNAL
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return []
    return rows


def _decided_keys() -> set[tuple[str, str]]:
    decided: set[tuple[str, str]] = set()
    for row in _events():
        if row.get("topic") not in {"approval.approved", "approval.rejected"}:
            continue
        payload = row.get("payload") or {}
        plan_id, action_id = str(payload.get("plan_id", "")), str(payload.get("action_id", ""))
        if plan_id and action_id:
            decided.add((plan_id, action_id))
    return decided


def pending() -> dict[str, Any]:
    decided = _decided_keys()
    rows = _events()
    receipts: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.get("topic") == "receipt.created":
            payload = row.get("payload") or {}
            rid = str(payload.get("id", ""))
            if rid:
                receipts[rid] = payload

    for row in reversed(rows):
        if row.get("topic") != "approval.required":
            continue
        payload = row.get("payload") or {}
        plan_id = str(payload.get("plan_id", ""))
        action_id = str(payload.get("action_id", ""))
        receipt_id = str(payload.get("receipt_id", ""))
        if not ID_RE.fullmatch(plan_id) or not ID_RE.fullmatch(action_id):
            continue
        if (plan_id, action_id) in decided:
            continue
        try:
            state = load_plan(plan_id)
            plan = state.plan
        except Exception:
            continue
        action = next((a for a in plan.get("actions", []) if str(a.get("id")) == action_id), None)
        if not isinstance(action, dict):
            continue
        receipt = receipts.get(receipt_id, {})
        runtime = ((receipt.get("evidence") or {}).get("runtime") or {}) if isinstance(receipt, dict) else {}
        return {
            "pending": True,
            "plan_id": plan_id,
            "action_id": action_id,
            "goal_id": str(plan.get("goal_id", "")),
            "tool": str(action.get("tool", "Action système")),
            "capability": str(action.get("capability", "")),
            "risk": str(action.get("risk", "unknown")),
            "reversible": bool(action.get("reversible", False)),
            "arguments": _redact(action.get("arguments", {})),
            "decision": _redact(runtime.get("decision", {})),
            "simulation": _redact(runtime.get("simulation", {})),
            "requested_at": float(row.get("ts", 0.0) or 0.0),
        }
    return {"pending": False}


def _record(topic: str, current: dict[str, Any]) -> None:
    payload = {
        "plan_id": current["plan_id"],
        "action_id": current["action_id"],
        "goal_id": current.get("goal_id", ""),
        "ts": time.time(),
    }
    try:
        BUS.emit(topic, payload, "qapproval_bridge", current.get("goal_id") or None)
    except OSError:
        pass


def approve(plan_id: str, action_id: str) -> dict[str, Any]:
    current = pending()
    if not current.get("pending"):
        return {"ok": False, "error": "no-pending-approval"}
    if plan_id != current["plan_id"] or action_id != current["action_id"]:
        return {"ok": False, "error": "approval-mismatch"}
    _record("approval.approved", current)
    # Scope approval to exactly one action. Then continue normally with approval=False.
    first = execute_plan(plan_id, approved=True, max_actions=1)
    result: dict[str, Any] = {"ok": bool(first.get("ok")) or first.get("stage") == "paused", "approved_action": action_id, "first": first}
    if first.get("stage") == "paused":
        result["continued"] = execute_plan(plan_id, approved=False)
    return result


def reject(plan_id: str, action_id: str) -> dict[str, Any]:
    current = pending()
    if not current.get("pending"):
        return {"ok": False, "error": "no-pending-approval"}
    if plan_id != current["plan_id"] or action_id != current["action_id"]:
        return {"ok": False, "error": "approval-mismatch"}
    try:
        update_plan(plan_id, state="cancelled")
        if current.get("goal_id"):
            update_goal(current["goal_id"], state="cancelled", last_error="user_rejected")
    except (OSError, ValueError):
        return {"ok": False, "error": "state-update-failed"}
    _record("approval.rejected", current)
    return {"ok": True, "rejected": action_id, "plan_id": plan_id}


def main() -> int:
    parser = argparse.ArgumentParser(description="Quantic human approval bridge")
    parser.add_argument("command", choices=("pending", "approve", "reject"))
    parser.add_argument("plan_id", nargs="?")
    parser.add_argument("action_id", nargs="?")
    args = parser.parse_args()
    if args.command == "pending":
        out = pending()
    elif not args.plan_id or not args.action_id:
        out = {"ok": False, "error": "plan-and-action-required"}
    elif args.command == "approve":
        out = approve(args.plan_id, args.action_id)
    else:
        out = reject(args.plan_id, args.action_id)
    print(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    return 0 if out.get("ok", True) or args.command == "pending" else 2


if __name__ == "__main__":
    raise SystemExit(main())
