#!/usr/bin/env python3
"""Q-Verify — deterministic post-execution verification for Quantic OS."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import json


@dataclass
class Verification:
    passed: bool
    checks: list[str]
    failures: list[str]
    severity: str


def verify(tool: str, result: dict[str, Any], before: dict[str, Any] | None = None, after: dict[str, Any] | None = None) -> Verification:
    checks: list[str] = []
    failures: list[str] = []
    if not isinstance(result, dict):
        failures.append("tool result is not structured")
    elif not result.get("ok", False):
        failures.append("tool reported failure")
    else:
        checks.append("tool reported success")

    if before is not None and after is not None:
        checks.append("before/after snapshots available")
        before_mounts = set(before.get("mounts", []))
        after_mounts = set(after.get("mounts", []))
        suspicious = [m for m in after_mounts - before_mounts if " rw" in m and ("/dev/nvme" in m or "/dev/sd" in m)]
        if suspicious:
            failures.append("new writable block-device mount detected")

    severity = "critical" if any("writable block-device" in f for f in failures) else ("error" if failures else "ok")
    return Verification(not failures, checks, failures, severity)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("tool")
    p.add_argument("result")
    args = p.parse_args()
    print(json.dumps(asdict(verify(args.tool, json.loads(args.result))), indent=2, ensure_ascii=False))
