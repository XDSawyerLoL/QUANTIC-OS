#!/usr/bin/env python3
"""Quantic Companion persistent event loop.

Runs fully in user space, keeps memory on QUANTIC-DATA when available, observes
resource pressure and accepts local JSON events through an inbox directory.
It never performs privileged shell execution.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from qcompanion import CompanionMemory, CompanionEngine, state_directory
from qresource import snapshot, plan

PERSISTENCE_STATUS = Path("/run/quantic/persistence.json")
PERSISTENT_USER_ROOT = Path("/var/lib/quantic/users")


def choose_state() -> Path:
    # Q-Persistence binds QUANTIC-DATA/quantic-state to /var/lib/quantic.
    # Keep each unprivileged companion below that durable tree; the shared
    # parent is created with the sticky bit by qpersistence.py.
    target = state_directory(
        status_path=PERSISTENCE_STATUS,
        persistent_user_root=PERSISTENT_USER_ROOT,
    )
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    target.chmod(0o700)
    return target


def atomic_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def consume_inbox(engine: CompanionEngine, state: Path) -> None:
    inbox = state / "events"
    done = state / "events-processed"
    inbox.mkdir(exist_ok=True)
    done.mkdir(exist_ok=True)
    for event_file in sorted(inbox.glob("*.json"))[:20]:
        try:
            event = json.loads(event_file.read_text(encoding="utf-8"))
            item = engine.consider(event)
            if item:
                atomic_json(state / "last-initiative.json", item.__dict__)
            event_file.replace(done / event_file.name)
        except Exception as exc:
            atomic_json(state / "last-error.json", {"source": event_file.name, "error": str(exc), "time": int(time.time())})
            event_file.unlink(missing_ok=True)


def main() -> None:
    state = choose_state()
    state.mkdir(parents=True, exist_ok=True)
    mem = CompanionMemory(state / "companion.db")
    engine = CompanionEngine(mem, cooldown_s=1800)
    mem.remember("companion:state_path", str(state))
    mem.remember("companion:started_at", int(time.time()))

    while True:
        s = snapshot()
        p = plan(s)
        if s.ram_percent >= 85:
            item = engine.consider({
                "type": "resource_pressure",
                "resource": "mémoire",
                "severity": s.ram_percent / 100,
            })
            if item:
                atomic_json(state / "last-initiative.json", item.__dict__)
        mem.remember("session:last_resource_plan", p.__dict__)
        atomic_json(state / "heartbeat.json", {
            "time": int(time.time()),
            "workload": p.workload,
            "objective": p.objective,
            "persistent": state == PERSISTENT_USER_ROOT or PERSISTENT_USER_ROOT in state.parents,
        })
        consume_inbox(engine, state)
        time.sleep(20)


if __name__ == "__main__":
    main()
