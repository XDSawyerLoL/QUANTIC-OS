#!/usr/bin/env python3
"""Minimal persistent companion event loop. No privileged shell execution."""
import json, os, time
from pathlib import Path
from qcompanion import CompanionMemory, CompanionEngine
from qresource import snapshot, plan

state = Path(os.environ.get("QUANTIC_STATE", str(Path.home()/".local/share/quantic")))
state.mkdir(parents=True, exist_ok=True)
mem = CompanionMemory(state/"companion.db")
engine = CompanionEngine(mem, cooldown_s=1800)
while True:
    s = snapshot(); p = plan(s)
    if s.ram_percent >= 85:
        item = engine.consider({"type":"resource_pressure","resource":"mémoire","severity":s.ram_percent/100})
        if item: (state/"last-initiative.json").write_text(json.dumps(item.__dict__, ensure_ascii=False))
    mem.remember("session:last_resource_plan", p.__dict__)
    time.sleep(30)
