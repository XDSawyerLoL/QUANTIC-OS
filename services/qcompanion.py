#!/usr/bin/env python3
"""Q-Companion — local autonomy/presence prototype for Quantic OS.

The companion stores local memories and turns trusted local events into
proactive initiatives. It deliberately separates *initiative* from privileged
execution: an initiative can propose, remind or request a tool action while the
OS permission layer remains authoritative.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

PERSISTENCE_STATUS = Path("/run/quantic/persistence.json")
PERSISTENT_USER_ROOT = Path("/var/lib/quantic/users")


def state_directory(
    *,
    status_path: Path | None = None,
    persistent_user_root: Path | None = None,
) -> Path:
    """Resolve the one companion state directory shared by daemon and UI."""
    explicit = os.environ.get("QUANTIC_STATE")
    if explicit:
        return Path(explicit)
    status_path = status_path or PERSISTENCE_STATUS
    persistent_user_root = persistent_user_root or PERSISTENT_USER_ROOT
    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if data.get("mode") == "persistent":
        return persistent_user_root / str(os.getuid())
    return Path.home() / ".local/share/quantic"


@dataclass
class Initiative:
    kind: str
    message: str
    priority: int = 50
    action: str | None = None
    requires_confirmation: bool = False


class CompanionMemory:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS initiatives (
                fingerprint TEXT PRIMARY KEY,
                last_emitted INTEGER NOT NULL
            )
        """)
        self.db.commit()

    def remember(self, key: str, value: Any) -> None:
        raw = json.dumps(value, ensure_ascii=False)
        self.db.execute(
            "INSERT INTO memory(key,value,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
            (key, raw, int(time.time())),
        )
        self.db.commit()

    def recall(self, key: str, default: Any = None) -> Any:
        row = self.db.execute("SELECT value FROM memory WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def list_prefix(self, prefix: str = "", limit: int = 50) -> dict[str, Any]:
        rows = self.db.execute(
            "SELECT key,value FROM memory WHERE key LIKE ? ORDER BY updated_at DESC LIMIT ?",
            (prefix + "%", limit),
        ).fetchall()
        return {key: json.loads(value) for key, value in rows}

    def cooldown_ok(self, fingerprint: str, cooldown_s: int, now: int | None = None) -> bool:
        now = int(time.time()) if now is None else now
        row = self.db.execute(
            "SELECT last_emitted FROM initiatives WHERE fingerprint=?", (fingerprint,)
        ).fetchone()
        return not row or now - int(row[0]) >= cooldown_s

    def mark_emitted(self, fingerprint: str, now: int | None = None) -> None:
        now = int(time.time()) if now is None else now
        self.db.execute(
            "INSERT INTO initiatives(fingerprint,last_emitted) VALUES(?,?) "
            "ON CONFLICT(fingerprint) DO UPDATE SET last_emitted=excluded.last_emitted",
            (fingerprint, now),
        )
        self.db.commit()


def initiative_from_event(event: dict[str, Any]) -> Initiative | None:
    """Small deterministic policy layer; LLM phrasing can be added afterward."""
    etype = event.get("type")
    if etype == "resource_pressure" and float(event.get("severity", 0)) >= 0.75:
        resource = event.get("resource", "resource")
        return Initiative(
            "system_help",
            f"Je détecte une forte pression {resource}. Je peux alléger les tâches secondaires.",
            priority=85,
            action="q-resource.optimize",
            requires_confirmation=False,
        )
    if etype == "goal_stalled" and int(event.get("days", 0)) >= 3:
        goal = event.get("goal", "cet objectif")
        return Initiative(
            "goal_followup",
            f"{goal} n'a pas avancé depuis quelques jours. Je peux t'aider à reprendre là où tu t'es arrêté.",
            priority=60,
        )
    if etype == "update_candidate_ready":
        return Initiative(
            "maintenance",
            "Une amélioration Quantic a passé ses tests. Q-Guardian peut la vérifier et la déployer automatiquement.",
            priority=45,
            action="q-safe-update.assess",
            requires_confirmation=False,
        )
    if etype == "security_anomaly":
        return Initiative(
            "security",
            "J'ai détecté un comportement inhabituel. Je peux isoler le processus pendant l'analyse.",
            priority=100,
            action="q-containment.isolate",
            requires_confirmation=False,
        )
    return None


class CompanionEngine:
    def __init__(self, memory: CompanionMemory, cooldown_s: int = 3600):
        self.memory = memory
        self.cooldown_s = cooldown_s

    def consider(self, event: dict[str, Any], now: int | None = None) -> Initiative | None:
        initiative = initiative_from_event(event)
        if not initiative:
            return None
        fp = f"{initiative.kind}:{event.get('type')}:{event.get('resource','')}:{event.get('goal','')}"
        if not self.memory.cooldown_ok(fp, self.cooldown_s, now):
            return None
        self.memory.mark_emitted(fp, now)
        return initiative


def main() -> None:
    p = argparse.ArgumentParser(description="Quantic local companion initiative prototype")
    p.add_argument("--memory", default=str(Path.home() / ".local/share/quantic/companion.db"))
    p.add_argument("--event", help="JSON event")
    args = p.parse_args()
    if not args.event:
        raise SystemExit("Provide --event '{...}'")
    engine = CompanionEngine(CompanionMemory(Path(args.memory)))
    result = engine.consider(json.loads(args.event))
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2) if result else "null")


if __name__ == "__main__":
    main()
