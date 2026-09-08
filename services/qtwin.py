#!/usr/bin/env python3
"""Q-Twin — live system snapshots plus candidate-vs-baseline regression checks."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path("/var/lib/quantic/twin")

@dataclass
class TwinVerdict:
    passed: bool
    score: float
    regressions: list[str]
    improvements: list[str]

@dataclass
class SystemSnapshot:
    ts: float
    hostname: str
    kernel: str
    machine: str
    boot_id: str
    root_free: int
    load1: float
    mounts: list[str]

DIRECTION = {
    "boot_seconds": -1,
    "latency_ms": -1,
    "frametime_p99_ms": -1,
    "idle_ram_mb": -1,
    "power_watts": -1,
    "fps_1pct_low": 1,
    "fps_avg": 1,
    "tokens_per_second": 1,
    "compile_jobs_per_min": 1,
}

def compare(baseline: dict[str, float], candidate: dict[str, float], max_regression_pct: float = 3.0) -> TwinVerdict:
    regressions: list[str] = []
    improvements: list[str] = []
    deltas = []
    for name, old in baseline.items():
        if name not in candidate or not isinstance(old, (int, float)) or old == 0:
            continue
        new = candidate[name]
        direction = DIRECTION.get(name, 1)
        raw_pct = (new - old) / abs(old) * 100
        benefit_pct = raw_pct * direction
        deltas.append(benefit_pct)
        if benefit_pct < -max_regression_pct:
            regressions.append(f"{name}: {benefit_pct:.1f}%")
        elif benefit_pct > max_regression_pct:
            improvements.append(f"{name}: +{benefit_pct:.1f}%")
    score = sum(deltas) / len(deltas) if deltas else 0.0
    return TwinVerdict(not regressions, round(score, 2), regressions, improvements)

def _read(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return ""

def capture() -> SystemSnapshot:
    usage = shutil.disk_usage("/")
    try: load1 = os.getloadavg()[0]
    except OSError: load1 = 0.0
    mounts: list[str] = []
    try:
        for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
            p = line.split()
            if len(p) >= 4: mounts.append(f"{p[0]} {p[1]} {p[3]}")
    except OSError:
        pass
    return SystemSnapshot(time.time(), platform.node(), platform.release(), platform.machine(), _read("/proc/sys/kernel/random/boot_id"), usage.free, load1, sorted(mounts))

def persist_snapshot(snapshot: SystemSnapshot, label: str = "snapshot") -> Path:
    ROOT.mkdir(parents=True, exist_ok=True)
    path = ROOT / f"{label}-{int(snapshot.ts)}.json"
    path.write_text(json.dumps(asdict(snapshot), indent=2), encoding="utf-8")
    return path

def state_diff(before: SystemSnapshot, after: SystemSnapshot) -> dict:
    return {
        "boot_changed": before.boot_id != after.boot_id,
        "root_free_delta": after.root_free - before.root_free,
        "load1_delta": round(after.load1 - before.load1, 3),
        "mounts_added": sorted(set(after.mounts) - set(before.mounts)),
        "mounts_removed": sorted(set(before.mounts) - set(after.mounts)),
    }

def main() -> None:
    p = argparse.ArgumentParser(description="Quantic Q-Twin")
    p.add_argument("baseline", nargs="?")
    p.add_argument("candidate", nargs="?")
    p.add_argument("--max-regression", type=float, default=3.0)
    p.add_argument("--snapshot", action="store_true")
    args = p.parse_args()
    if args.snapshot:
        s = capture(); persist_snapshot(s); print(json.dumps(asdict(s), indent=2)); return
    if not args.baseline or not args.candidate:
        raise SystemExit("baseline and candidate are required unless --snapshot is used")
    b = json.loads(Path(args.baseline).read_text())
    c = json.loads(Path(args.candidate).read_text())
    print(json.dumps(asdict(compare(b, c, args.max_regression)), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
