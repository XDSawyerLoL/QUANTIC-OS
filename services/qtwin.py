#!/usr/bin/env python3
"""Q-Twin — compare an improvement candidate against last-known-good metrics."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class TwinVerdict:
    passed: bool
    score: float
    regressions: list[str]
    improvements: list[str]


# Lower is better for latency/power/memory; higher is better for throughput/fps.
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


def main() -> None:
    p = argparse.ArgumentParser(description="Quantic Q-Twin metric comparison")
    p.add_argument("baseline")
    p.add_argument("candidate")
    p.add_argument("--max-regression", type=float, default=3.0)
    args = p.parse_args()
    b = json.loads(Path(args.baseline).read_text())
    c = json.loads(Path(args.candidate).read_text())
    print(json.dumps(asdict(compare(b, c, args.max_regression)), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
