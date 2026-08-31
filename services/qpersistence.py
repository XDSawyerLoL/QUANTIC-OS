#!/usr/bin/env python3
"""Quantic persistence broker.

Finds a removable filesystem labelled QUANTIC-DATA, mounts it safely, and
binds durable Quantic state into /var/lib/quantic. If no persistence volume is
present, Quantic continues in ephemeral mode without blocking the desktop.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

STATE = Path("/var/lib/quantic")
RUNTIME = Path("/run/quantic")
MOUNT = Path("/run/quantic/persist")
LABEL = os.environ.get("QUANTIC_PERSIST_LABEL", "QUANTIC-DATA")


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True, capture_output=True)


def device_for_label() -> str | None:
    p = run("blkid", "-L", LABEL, check=False)
    dev = p.stdout.strip()
    return dev or None


def ensure_dirs() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    STATE.mkdir(parents=True, exist_ok=True)
    MOUNT.mkdir(parents=True, exist_ok=True)


def mount_persistence(dev: str) -> bool:
    if run("mountpoint", "-q", str(MOUNT), check=False).returncode != 0:
        p = run("mount", "-o", "rw,nosuid,nodev", dev, str(MOUNT), check=False)
        if p.returncode != 0:
            return False
    durable = MOUNT / "quantic-state"
    durable.mkdir(parents=True, exist_ok=True)
    if run("mountpoint", "-q", str(STATE), check=False).returncode != 0:
        run("mount", "--bind", str(durable), str(STATE))
    return True


def write_status(mode: str, device: str | None = None) -> None:
    (RUNTIME / "persistence.json").write_text(
        json.dumps({"mode": mode, "label": LABEL, "device": device}, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    ensure_dirs()
    dev = device_for_label()
    if not dev:
        write_status("ephemeral")
        return 0
    if mount_persistence(dev):
        write_status("persistent", dev)
        return 0
    write_status("degraded", dev)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
