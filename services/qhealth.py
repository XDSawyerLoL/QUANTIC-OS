#!/usr/bin/env python3
"""Quantic health sentinel.

Writes a machine-readable health snapshot for Quantic Home and the Companion.
It never repairs privileged state by itself; it reports and lets policy decide.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

OUT = Path("/run/quantic/health.json")


def cmd(*args: str) -> tuple[int, str]:
    p = subprocess.run(args, text=True, capture_output=True)
    return p.returncode, (p.stdout or p.stderr).strip()


def systemd_state(unit: str) -> str:
    rc, out = cmd("systemctl", "is-active", unit)
    return out if out else ("active" if rc == 0 else "unknown")


def root_free_gib() -> float:
    u = shutil.disk_usage("/")
    return round(u.free / 1024**3, 2)


def snapshot() -> dict:
    return {
        "timestamp": int(time.time()),
        "status": "ok",
        "persistence": json.loads(Path("/run/quantic/persistence.json").read_text()) if Path("/run/quantic/persistence.json").exists() else {"mode": "unknown"},
        "usb_safe": systemd_state("quantic-usb-safe.service"),
        "persistence_service": systemd_state("quantic-persistence.service"),
        "root_free_gib": root_free_gib(),
        "network_manager": systemd_state("NetworkManager.service"),
    }


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = snapshot()
    if data["usb_safe"] != "active":
        data["status"] = "attention"
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
