#!/usr/bin/env python3
"""Q-Resource — adaptive resource policy prototype.

It observes pressure and classifies workloads, then emits a reversible plan. The
real ISO can map these plans to cgroup v2 / sched_ext / power profiles. The V0.1
user-space implementation intentionally avoids unsafe kernel tweaks.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from enum import Enum

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


class Workload(str, Enum):
    IDLE = "idle"
    INTERACTIVE = "interactive"
    GAMING = "gaming"
    STREAMING = "streaming"
    AI = "ai"
    BUILD = "build"
    BALANCED = "balanced"


GAME_HINTS = {"steam", "proton", "wine", "lutris", "heroic", "gamescope"}
STREAM_HINTS = {"obs", "obs64", "ffmpeg"}
AI_HINTS = {"ollama", "llama-server", "vllm", "python"}
BUILD_HINTS = {"cargo", "rustc", "gcc", "g++", "clang", "ninja", "make", "gradle", "javac"}


@dataclass
class ResourceSnapshot:
    cpu_percent: float
    ram_percent: float
    swap_percent: float
    load_1m: float
    process_names: list[str]


@dataclass
class ResourcePlan:
    workload: str
    objective: str
    actions: list[str]
    confidence: float
    reversible: bool = True


def snapshot() -> ResourceSnapshot:
    if not psutil:
        return ResourceSnapshot(0, 0, 0, 0, [])
    names = []
    for proc in psutil.process_iter(["name"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name:
                names.append(name)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
    return ResourceSnapshot(
        cpu_percent=psutil.cpu_percent(interval=0.05),
        ram_percent=psutil.virtual_memory().percent,
        swap_percent=psutil.swap_memory().percent,
        load_1m=round(load, 2),
        process_names=names,
    )


def _contains(names: list[str], hints: set[str]) -> bool:
    return any(any(h in name for h in hints) for name in names)


def classify(s: ResourceSnapshot) -> Workload:
    if _contains(s.process_names, STREAM_HINTS):
        return Workload.STREAMING
    if _contains(s.process_names, GAME_HINTS):
        return Workload.GAMING
    if _contains(s.process_names, AI_HINTS) and (s.cpu_percent > 35 or s.ram_percent > 45):
        return Workload.AI
    if _contains(s.process_names, BUILD_HINTS):
        return Workload.BUILD
    if s.cpu_percent < 8 and s.ram_percent < 45:
        return Workload.IDLE
    return Workload.BALANCED


def plan(s: ResourceSnapshot) -> ResourcePlan:
    w = classify(s)
    actions: list[str] = []
    objective = "fluidité générale"
    confidence = 0.7
    if w == Workload.GAMING:
        objective = "frametime régulier et latence basse"
        actions += ["prioritize interactive/game cgroup", "defer background indexing", "protect audio latency"]
        confidence = 0.86
    elif w == Workload.STREAMING:
        objective = "encodage stable sans frame perdue"
        actions += ["protect OBS/encoder CPU budget", "deprioritize background I/O", "preserve audio thread latency"]
        confidence = 0.9
    elif w == Workload.AI:
        objective = "débit IA sans figer le bureau"
        actions += ["reserve interactive CPU headroom", "favor model process memory locality", "avoid competing GPU background work"]
        confidence = 0.84
    elif w == Workload.BUILD:
        objective = "débit CPU multi-cœur"
        actions += ["allow broad CPU parallelism", "raise build I/O weight while interactive headroom remains"]
        confidence = 0.82
    elif w == Workload.IDLE:
        objective = "économie et maintenance discrète"
        actions += ["allow safe maintenance", "prepare likely caches", "prefer energy-efficient scheduling"]
        confidence = 0.75
    else:
        actions += ["keep balanced scheduler policy"]

    if s.ram_percent >= 85:
        actions += ["reduce background memory pressure", "prefer reclaim of cold caches before interactive pages"]
    if s.cpu_percent >= 90:
        actions += ["cap low-priority background CPU groups"]
    return ResourcePlan(w.value, objective, actions, confidence)


def main() -> None:
    p = argparse.ArgumentParser(description="Quantic adaptive resource planner")
    p.add_argument("--watch", type=int, default=0, help="refresh every N seconds")
    args = p.parse_args()
    while True:
        s = snapshot()
        print(json.dumps({"snapshot": asdict(s), "plan": asdict(plan(s))}, indent=2, ensure_ascii=False))
        if not args.watch:
            break
        time.sleep(max(1, args.watch))


if __name__ == "__main__":
    main()
