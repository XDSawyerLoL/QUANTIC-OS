#!/usr/bin/env python3
"""Q-Containment: fail-closed process sandbox for approved Quantic actions."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import shutil
import subprocess
import time


@dataclass
class ContainedResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    sandboxed: bool
    duration_ms: int


def available() -> bool:
    return shutil.which("bwrap") is not None


def _validate_argv(argv: list[str]) -> None:
    if not argv or not isinstance(argv, list) or not all(isinstance(x, str) and x for x in argv):
        raise ValueError("argv must be a non-empty list of strings")
    forbidden = {"sudo", "su", "pkexec", "mount", "umount", "fdisk", "parted", "mkfs", "dd", "grub2-install"}
    exe = Path(argv[0]).name
    if exe in forbidden:
        raise PermissionError(f"forbidden executable in containment: {exe}")


def run(argv: list[str], *, allow_network: bool = False, writable: list[str] | None = None, timeout: int = 60) -> ContainedResult:
    _validate_argv(argv)
    start = time.monotonic()
    writable = writable or []
    bwrap = shutil.which("bwrap")
    if not bwrap:
        return ContainedResult(False, 126, "", "bubblewrap unavailable; fail closed", False, 0)

    command = [
        bwrap, "--die-with-parent", "--new-session",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/etc", "/etc",
        "--ro-bind", "/bin", "/bin",
        "--ro-bind", "/lib", "/lib",
        "--ro-bind-try", "/lib64", "/lib64",
        "--proc", "/proc", "--dev", "/dev",
        "--tmpfs", "/tmp", "--dir", "/tmp/quantic-home",
        "--setenv", "HOME", "/tmp/quantic-home",
    ]
    if not allow_network:
        command += ["--unshare-net"]
    for item in writable:
        p = Path(item).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(str(p))
        command += ["--bind", str(p), str(p)]
    command += ["--"] + argv

    try:
        cp = subprocess.run(command, text=True, capture_output=True, timeout=max(1, min(timeout, 300)), check=False)
        elapsed = int((time.monotonic() - start) * 1000)
        return ContainedResult(cp.returncode == 0, cp.returncode, cp.stdout, cp.stderr, True, elapsed)
    except subprocess.TimeoutExpired as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        return ContainedResult(False, 124, exc.stdout or "", exc.stderr or "timeout", True, elapsed)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Quantic containment runner")
    ap.add_argument("--network", action="store_true")
    ap.add_argument("command", nargs="+")
    ns = ap.parse_args()
    print(json.dumps(asdict(run(ns.command, allow_network=ns.network)), indent=2))
