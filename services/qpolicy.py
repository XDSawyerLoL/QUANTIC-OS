#!/usr/bin/env python3
"""Quantic deterministic permission boundary for agent actions."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json, time

SAFE_READ={"file.read","file.search","system.inspect","memory.read","simulation.read"}
APPROVAL={"file.write","app.launch","connector.read","connector.write","network.request","system.change","package.install"}
DENY={"disk.raw_write","bootloader.write","internal_disk.mount_rw","security.disable","sandbox.disable"}
AUDIT=Path("/var/lib/quantic/audit/agent.jsonl")

@dataclass
class Decision:
    action:str; verdict:str; reason:str; sandbox:bool=True

def decide(action:str, sandbox_available:bool=True)->Decision:
    if action in DENY: d=Decision(action,"deny","protected Quantic boundary")
    elif action in SAFE_READ: d=Decision(action,"allow","local read-only capability")
    elif action in APPROVAL: d=Decision(action,"approval","explicit user approval required")
    else: d=Decision(action,"deny","unknown capability: fail closed")
    if d.verdict != "deny" and not sandbox_available and action not in SAFE_READ:
        d=Decision(action,"deny","sandbox unavailable: fail closed",False)
    return d

def audit(decision:Decision, metadata:dict|None=None)->None:
    try:
        AUDIT.parent.mkdir(parents=True,exist_ok=True)
        row={"ts":time.time(),**asdict(decision),"metadata":metadata or {}}
        with AUDIT.open("a",encoding="utf-8") as f: f.write(json.dumps(row,ensure_ascii=False)+"\n")
    except OSError: pass
