#!/usr/bin/env python3
"""Q-Containment — sandbox plan for unknown/untrusted applications."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class SandboxPlan:
    backend: str
    command: list[str] | None
    network: str
    home_access: str
    note: str


def sandbox_plan(command: list[str], allow_network: bool = False) -> SandboxPlan:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        return SandboxPlan("none", None, "unchanged", "unchanged", "bubblewrap is not installed; do not auto-run unknown software.")
    cmd = [
        bwrap,
        "--die-with-parent",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/etc", "/etc",
        "--dev", "/dev",
        "--proc", "/proc",
        "--tmpfs", "/tmp",
        "--tmpfs", str(Path.home()),
    ]
    if not allow_network:
        cmd.append("--unshare-net")
    cmd += ["--"] + command
    return SandboxPlan("bubblewrap", cmd, "allowed" if allow_network else "blocked", "ephemeral", "Unknown app starts with a disposable home and read-only system view.")


def main() -> None:
    p = argparse.ArgumentParser(description="Quantic sandbox launcher")
    p.add_argument("command", nargs="+")
    p.add_argument("--network", action="store_true")
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    plan = sandbox_plan(args.command, args.network)
    print(json.dumps(asdict(plan), indent=2))
    if args.execute:
        if not plan.command:
            raise SystemExit("No safe sandbox backend available")
        subprocess.run(plan.command, check=False)


if __name__ == "__main__":
    main()
