#!/usr/bin/env python3
"""Q-Simulation: deterministic pre-execution impact gate for Quantic actions."""
from __future__ import annotations
import json, time, uuid
from dataclasses import dataclass, asdict
from pathlib import Path

LEVELS = ("PLAN", "SANDBOX", "SHADOW", "CANARY", "COMMIT", "ROLLBACK")
RISK = {"read": 0, "inspect": 0, "write": 2, "network": 2, "install": 3, "service": 3, "disk": 5, "boot": 5, "security": 5}

@dataclass
class Simulation:
    id: str
    action: str
    category: str
    level: str
    risk: int
    reversible: bool
    requires_approval: bool
    verdict: str
    reason: str
    created: float


def evaluate(action: str, category: str, reversible: bool = True, requested_level: str = "SANDBOX") -> Simulation:
    level = requested_level.upper()
    if level not in LEVELS: level = "SANDBOX"
    risk = RISK.get(category, 4)
    approval = risk >= 2 or level in {"CANARY", "COMMIT"}
    if risk >= 5 and not reversible:
        verdict, reason = "BLOCK", "critical irreversible action"
    elif level == "COMMIT" and risk >= 4:
        verdict, reason = "REQUIRE_SIMULATION", "critical action must pass sandbox/shadow first"
    elif approval:
        verdict, reason = "REQUIRE_APPROVAL", "impactful action requires explicit policy approval"
    else:
        verdict, reason = "ALLOW", "low-risk reversible operation"
    return Simulation(str(uuid.uuid4()), action, category, level, risk, reversible, approval, verdict, reason, time.time())


def persist(sim: Simulation, root: Path = Path("/var/lib/quantic/simulations")) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    p = root / f"{sim.id}.json"
    p.write_text(json.dumps(asdict(sim), indent=2), encoding="utf-8")
    return p

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("action"); ap.add_argument("--category", default="inspect"); ap.add_argument("--level", default="SANDBOX"); ap.add_argument("--irreversible", action="store_true")
    a=ap.parse_args(); s=evaluate(a.action,a.category,not a.irreversible,a.level); print(json.dumps(asdict(s),indent=2))
