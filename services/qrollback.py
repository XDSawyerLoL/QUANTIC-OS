#!/usr/bin/env python3
"""Q-Rollback — transactional rollback journal for reversible Quantic actions."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json, time, uuid

ROOT = Path("/var/lib/quantic/rollback")


@dataclass
class RollbackRecord:
    id: str
    tool: str
    created: float
    reversible: bool
    state: str
    payload: dict[str, Any]


def begin(tool: str, payload: dict[str, Any], reversible: bool) -> RollbackRecord:
    rec = RollbackRecord(str(uuid.uuid4()), tool, time.time(), reversible, "prepared", payload)
    persist(rec)
    return rec


def persist(rec: RollbackRecord) -> Path:
    ROOT.mkdir(parents=True, exist_ok=True)
    p = ROOT / f"{rec.id}.json"
    p.write_text(json.dumps(asdict(rec), indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def mark(rec: RollbackRecord, state: str) -> RollbackRecord:
    rec.state = state
    persist(rec)
    return rec


def rollback(rec: RollbackRecord) -> dict[str, Any]:
    if not rec.reversible:
        return {"ok": False, "reason": "action is not reversible", "record": rec.id}
    # V1 journal deliberately refuses to invent undo commands. Tool-specific
    # rollback handlers will be registered explicitly in the next layer.
    rec.state = "rollback_required"
    persist(rec)
    return {"ok": False, "reason": "manual/tool-specific rollback handler required", "record": rec.id}
