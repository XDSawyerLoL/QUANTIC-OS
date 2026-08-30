#!/usr/bin/env python3
"""Q-Doctor — compact health report for Quantic OS."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass

try:
    from .qhardware import discover
    from .qresource import snapshot, plan
except ImportError:
    from qhardware import discover
    from qresource import snapshot, plan


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _cmd(name: str, args: list[str] | None = None) -> Check:
    exe=shutil.which(name)
    if not exe: return Check(name,False,"not installed")
    if not args: return Check(name,True,exe)
    try:
        p=subprocess.run([exe]+args,text=True,capture_output=True,timeout=5)
        return Check(name,p.returncode==0,(p.stdout or p.stderr).strip()[:220])
    except Exception as exc: return Check(name,False,str(exc))


def report() -> dict:
    hw=discover(); snap=snapshot(); rplan=plan(snap)
    checks=[_cmd("python3",["--version"]),_cmd("wine",["--version"]),_cmd("ollama",["--version"]),_cmd("nmcli",["--version"]),_cmd("wpctl",["status"])]
    return {
        "schema":1,
        "hardware":asdict(hw),
        "resource_snapshot":asdict(snap),
        "resource_plan":asdict(rplan),
        "checks":[asdict(c) for c in checks],
        "healthy":all(c.ok for c in checks if c.name in {"python3","nmcli"}),
    }


def main():
    p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=report()
    if a.json: print(json.dumps(r,ensure_ascii=False,indent=2)); return
    print("QUANTIC DOCTOR")
    print("Healthy:","yes" if r["healthy"] else "attention")
    for c in r["checks"]: print(f"- {c['name']:<10} {'OK' if c['ok'] else 'WARN'}  {c['detail']}")


if __name__=="__main__": main()
