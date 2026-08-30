#!/usr/bin/env python3
"""Q-Benchmark — small repeatable baseline suite for Quantic optimization.

Not a marketing benchmark. It exists so Q-Twin has measurements from the same
machine before and after a candidate optimization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

import numpy as np


def _timed(fn, repeat: int = 1) -> float:
    start = time.perf_counter()
    for _ in range(repeat): fn()
    return time.perf_counter() - start


def cpu_hash_mb_s(size_mb: int = 32) -> float:
    data = b"q" * (size_mb * 1024 * 1024)
    t = _timed(lambda: hashlib.sha256(data).digest(), repeat=2)
    return round(size_mb * 2 / max(t, 1e-9), 2)


def memory_copy_gib_s(size_mb: int = 128) -> float:
    a = np.ones(size_mb * 1024 * 1024 // 8, dtype=np.float64)
    t = _timed(lambda: a.copy(), repeat=3)
    return round((size_mb * 3 / 1024) / max(t, 1e-9), 2)


def disk_write_mb_s(size_mb: int = 64) -> float:
    block = b"0" * (1024 * 1024)
    with tempfile.NamedTemporaryFile(delete=False) as f:
        path = f.name
        start = time.perf_counter()
        for _ in range(size_mb): f.write(block)
        f.flush(); os.fsync(f.fileno())
        t = time.perf_counter() - start
    Path(path).unlink(missing_ok=True)
    return round(size_mb / max(t, 1e-9), 2)


def run() -> dict:
    return {
        "schema": 1,
        "timestamp": int(time.time()),
        "cpu_hash_mb_s": cpu_hash_mb_s(),
        "memory_copy_gib_s": memory_copy_gib_s(),
        "disk_write_mb_s": disk_write_mb_s(),
    }


def main() -> None:
    p=argparse.ArgumentParser(description="Quantic local baseline benchmark")
    p.add_argument("--output")
    args=p.parse_args(); data=run(); raw=json.dumps(data,indent=2)+"\n"
    if args.output: Path(args.output).write_text(raw)
    print(raw,end="")


if __name__ == "__main__": main()
