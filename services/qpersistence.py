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
import pwd
import subprocess
from pathlib import Path

STATE = Path("/var/lib/quantic")
RUNTIME = Path("/run/quantic")
MOUNT = Path("/run/quantic/persist")
LABEL = os.environ.get("QUANTIC_PERSIST_LABEL", "QUANTIC-DATA")
LAYOUT = ("models", "memory", "index", "skills", "connectors", "tasks", "simulations", "audit", "vault")
NON_POSIX_FILESYSTEMS = {"vfat", "msdos", "exfat", "ntfs", "ntfs3", "fuseblk"}


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
    # Ephemeral mode still needs the complete writable runtime layout before
    # Ollama and the agent services start.
    initialise_layout(STATE)


def filesystem_type(dev: str) -> str:
    p = run("blkid", "-o", "value", "-s", "TYPE", dev, check=False)
    return p.stdout.strip().lower() if p.returncode == 0 else ""


def mount_options(fs_type: str) -> str:
    options = ["rw", "nosuid", "nodev", "noexec"]
    if fs_type in NON_POSIX_FILESYSTEMS:
        # Windows-prepared FAT/exFAT/NTFS volumes do not implement chmod or
        # chown.  Their permissions must be supplied at mount time so the
        # desktop companion and the dedicated Ollama user can both persist.
        options.extend(("uid=0", "gid=0", "fmask=0000", "dmask=0000"))
    return ",".join(options)


def prepare_ollama_directory(durable: Path) -> None:
    models = durable / "models" / "ollama"
    models.mkdir(parents=True, exist_ok=True)
    try:
        account = pwd.getpwnam("ollama")
    except KeyError:
        return
    try:
        os.chown(models, account.pw_uid, account.pw_gid)
        models.chmod(0o750)
    except OSError:
        # Non-POSIX media uses the explicit mount masks above instead.
        pass


def initialise_layout(durable: Path) -> None:
    for name in LAYOUT:
        (durable / name).mkdir(parents=True, exist_ok=True)
    prepare_ollama_directory(durable)
    users = durable / "users"
    users.mkdir(parents=True, exist_ok=True)
    try:
        users.chmod(0o1777)
    except OSError:
        # FAT/exFAT/NTFS permissions are defined by mount_options().
        pass


def mount_persistence(dev: str) -> bool:
    fs_type = filesystem_type(dev)
    if run("mountpoint", "-q", str(MOUNT), check=False).returncode != 0:
        p = run("mount", "-o", mount_options(fs_type), dev, str(MOUNT), check=False)
        if p.returncode != 0:
            return False
    durable = MOUNT / "quantic-state"
    durable.mkdir(parents=True, exist_ok=True)
    initialise_layout(durable)
    if run("mountpoint", "-q", str(STATE), check=False).returncode != 0:
        run("mount", "--bind", str(durable), str(STATE))
    return True


def write_status(mode: str, device: str | None = None, reason: str | None = None) -> None:
    payload = {"mode": mode, "label": LABEL, "device": device, "state": str(STATE)}
    if reason:
        payload["reason"] = reason
    (RUNTIME / "persistence.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


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
