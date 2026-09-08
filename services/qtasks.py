#!/usr/bin/env python3
"""Q-Tasks: persistent resumable task journal for long-running local agent work."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json, time, uuid

ROOT = Path("/var/lib/quantic/tasks")
VALID = {"queued", "running", "waiting_approval", "paused", "failed", "done", "rolled_back"}

@dataclass
class Task:
    id: str
    title: str
    tool: str
    arguments: dict
    state: str
    created: float
    updated: float
    attempts: int = 0
    last_error: str = ""


def _path(task_id: str) -> Path:
    return ROOT / f"{task_id}.json"


def save(task: Task) -> Path:
    if task.state not in VALID:
        raise ValueError("invalid task state")
    ROOT.mkdir(parents=True, exist_ok=True)
    task.updated = time.time()
    p = _path(task.id)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(task), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    return p


def create(title: str, tool: str, arguments: dict) -> Task:
    now = time.time()
    task = Task(str(uuid.uuid4()), title, tool, arguments, "queued", now, now)
    save(task)
    return task


def load(task_id: str) -> Task:
    row = json.loads(_path(task_id).read_text(encoding="utf-8"))
    return Task(**row)


def transition(task_id: str, state: str, error: str = "") -> Task:
    if state not in VALID:
        raise ValueError("invalid task state")
    task = load(task_id)
    task.state = state
    task.last_error = error
    if state == "running":
        task.attempts += 1
    save(task)
    return task


def resumable() -> list[Task]:
    if not ROOT.exists():
        return []
    out: list[Task] = []
    for p in sorted(ROOT.glob("*.json")):
        try:
            task = Task(**json.loads(p.read_text(encoding="utf-8")))
            if task.state in {"queued", "running", "paused"}:
                out.append(task)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return out

if __name__ == "__main__":
    print(json.dumps([asdict(x) for x in resumable()], ensure_ascii=False, indent=2))
