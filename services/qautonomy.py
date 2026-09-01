#!/usr/bin/env python3
"""Durable goal/plan state for Quantic V2 autonomy.

State is stored as atomic JSON documents so goals and plans survive reboot and
can be resumed without requiring an optional database service.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json
import time

try:
    from .qcontracts import Goal, Plan
except ImportError:
    from qcontracts import Goal, Plan

ROOT = Path("/var/lib/quantic/autonomy")
GOALS = ROOT / "goals"
PLANS = ROOT / "plans"
VALID_STATES = {"pending", "running", "paused", "waiting_approval", "done", "failed", "cancelled"}


@dataclass
class GoalState:
    goal: dict[str, Any]
    state: str = "pending"
    active_plan_id: str | None = None
    current_action: int = 0
    attempts: int = 0
    last_error: str = ""
    updated_at: float = 0.0


@dataclass
class PlanState:
    plan: dict[str, Any]
    state: str = "pending"
    next_action: int = 0
    completed_action_ids: list[str] | None = None
    last_receipt_id: str | None = None
    updated_at: float = 0.0

    def __post_init__(self) -> None:
        if self.completed_action_ids is None:
            self.completed_action_ids = []


def _atomic_write(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def _goal_path(goal_id: str) -> Path:
    return GOALS / f"{goal_id}.json"


def _plan_path(plan_id: str) -> Path:
    return PLANS / f"{plan_id}.json"


def save_goal(goal: Goal, *, state: str = "pending", active_plan_id: str | None = None) -> GoalState:
    if state not in VALID_STATES:
        raise ValueError("invalid goal state")
    row = GoalState(asdict(goal), state, active_plan_id, updated_at=time.time())
    _atomic_write(_goal_path(goal.id), asdict(row))
    return row


def save_plan(plan: Plan, *, state: str = "pending") -> PlanState:
    if state not in VALID_STATES:
        raise ValueError("invalid plan state")
    row = PlanState(asdict(plan), state, updated_at=time.time())
    _atomic_write(_plan_path(plan.id), asdict(row))
    return row


def load_goal(goal_id: str) -> GoalState:
    return GoalState(**json.loads(_goal_path(goal_id).read_text(encoding="utf-8")))


def load_plan(plan_id: str) -> PlanState:
    return PlanState(**json.loads(_plan_path(plan_id).read_text(encoding="utf-8")))


def update_goal(goal_id: str, **changes: Any) -> GoalState:
    row = load_goal(goal_id)
    for key, value in changes.items():
        if not hasattr(row, key):
            raise AttributeError(key)
        setattr(row, key, value)
    if row.state not in VALID_STATES:
        raise ValueError("invalid goal state")
    row.updated_at = time.time()
    _atomic_write(_goal_path(goal_id), asdict(row))
    return row


def update_plan(plan_id: str, **changes: Any) -> PlanState:
    row = load_plan(plan_id)
    for key, value in changes.items():
        if not hasattr(row, key):
            raise AttributeError(key)
        setattr(row, key, value)
    if row.state not in VALID_STATES:
        raise ValueError("invalid plan state")
    row.updated_at = time.time()
    _atomic_write(_plan_path(plan_id), asdict(row))
    return row


def resumable_goals() -> list[GoalState]:
    if not GOALS.exists():
        return []
    out: list[GoalState] = []
    for path in sorted(GOALS.glob("*.json")):
        try:
            row = GoalState(**json.loads(path.read_text(encoding="utf-8")))
            if row.state in {"pending", "running", "paused"}:
                out.append(row)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return out


def resumable_plans() -> list[PlanState]:
    if not PLANS.exists():
        return []
    out: list[PlanState] = []
    for path in sorted(PLANS.glob("*.json")):
        try:
            row = PlanState(**json.loads(path.read_text(encoding="utf-8")))
            if row.state in {"pending", "running", "paused"}:
                out.append(row)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return out
