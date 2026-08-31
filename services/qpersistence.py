#!/usr/bin/env python3
"""Quantic persistence broker.

Finds a *removable USB* filesystem labelled QUANTIC-DATA, mounts it safely,
and binds durable Quantic state into /var/lib/quantic. Internal disks are
explicitly rejected even if they carry the same label. If no valid persistence
volume is present, Quantic continues in ephemeral mode without blocking boot.
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


def removable_usb(dev: str) -> bool:
    p = run("lsblk", "-ndo", "RM,TRAN,RO", dev, check=False)
    if p.returncode != 0:
        return False
    fields = p.stdout.strip().split()
    if len(fields) < 3:
        parent = run("lsblk", "-ndo", "PKNAME", dev, check=False).stdout.strip()
        if not parent:
            return False
        p = run("lsblk", "-ndo", "RM,TRAN,RO", f"/dev/{parent}", check=False)
        fields = p.stdout.strip().split()
    if len(fields) < 3:
        return False
    rm, transport, ro = fields[0], fields[1].lower(), fields[2]
    return rm == "1" and transport == "usb" and ro == "0"


def ensure_dirs() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    STATE.mkdir(parents=True, exist_ok=True)
    MOUNT.mkdir(parents=True, exist_ok=True)


def mount_persistence(dev: str) -> bool:
    if run("mountpoint", "-q", str(MOUNT), check=False).returncode != 0:
        p = run("mount", "-o", "rw,nosuid,nodev,noexec", dev, str(MOUNT), check=False)
        if p.returncode != 0:
            return False
    durable = MOUNT / "quantic-state"
    durable.mkdir(parents=True, exist_ok=True)
    users = MOUNT / "users"
    users.mkdir(parents=True, exist_ok=True)
    users.chmod(0o1777)
    if run("mountpoint", "-q", str(STATE), check=False).returncode != 0:
        run("mount", "--bind", str(durable), str(STATE))
    return True


def write_status(mode: str, device: str | None = None, reason: str | None = None) -> None:
    payload = {"mode": mode, "label": LABEL, "device": device}
    if reason:
        payload["reason"] = reason
    (RUNTIME / "persistence.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def main() -> int:
    ensure_dirs()
    dev = device_for_label()
    if not dev:
        write_status("ephemeral", reason="no QUANTIC-DATA volume")
        return 0
    if not removable_usb(dev):
        write_status("ephemeral", dev, "label found but device is not a writable removable USB disk")
        return 0
    if mount_persistence(dev):
        write_status("persistent", dev)
        return 0
    write_status("degraded", dev, "mount failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
