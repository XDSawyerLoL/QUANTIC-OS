#!/usr/bin/env python3
"""Causal/temporal memory reasoner with fast System-1 and deliberate System-2 paths."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json, sqlite3, time, uuid

DEFAULT_DB=Path('/var/lib/quantic/memory/qmemory_reasoner.sqlite3')

def _id(p): return f'{p}_{uuid.uuid4().hex}'

@dataclass(frozen=True)
class ReasoningRoute:
    mode: str
    reason: str
    max_hops: int

class CausalMemory:
    def __init__(self,path:Path=DEFAULT_DB):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.path); self.db.row_factory=sqlite3.Row
        self.db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS facts(id TEXT PRIMARY KEY, subject TEXT, predicate TEXT, object TEXT, valid_from REAL, valid_to REAL, confidence REAL, memory_id TEXT, provenance_json TEXT, status TEXT);
        CREATE INDEX IF NOT EXISTS idx_facts_sp ON facts(subject,predicate,status,valid_from DESC);
        CREATE TABLE IF NOT EXISTS causal(id TEXT PRIMARY KEY, cause_id TEXT, effect_id TEXT, relation TEXT, confidence REAL, provenance_json TEXT);
        CREATE INDEX IF NOT EXISTS idx_causal_cause ON causal(cause_id,confidence DESC);
        '''); self.db.commit()
    def assert_fact(self,subject:str,predicate:str,obj:str,*,memory_id:str,provenance:dict[str,Any],confidence:float=1.0,ts:float|None=None):
        now=ts or time.time()
        current=self.db.execute("SELECT id,object FROM facts WHERE subject=? AND predicate=? AND status='active' ORDER BY valid_from DESC LIMIT 1",(subject,predicate)).fetchone()
        if current and current['object'] != obj:
            self.db.execute("UPDATE facts SET status='superseded',valid_to=? WHERE id=?",(now,current['id']))
        fid=_id('fact'); self.db.execute("INSERT INTO facts VALUES(?,?,?,?,?,?,?,?,?,?)",(fid,subject,predicate,obj,now,None,max(0,min(1,confidence)),memory_id,json.dumps(provenance,ensure_ascii=False),'active')); self.db.commit(); return fid
    def link_cause(self,cause_id:str,effect_id:str,*,relation:str='caused',confidence:float=1.0,provenance:dict[str,Any]|None=None):
        eid=_id('cause'); self.db.execute("INSERT INTO causal VALUES(?,?,?,?,?,?)",(eid,cause_id,effect_id,relation,max(0,min(1,confidence)),json.dumps(provenance or {},ensure_ascii=False))); self.db.commit(); return eid
    def current_fact(self,subject:str,predicate:str):
        row=self.db.execute("SELECT * FROM facts WHERE subject=? AND predicate=? AND status='active' ORDER BY valid_from DESC LIMIT 1",(subject,predicate)).fetchone(); return dict(row) if row else None
    def history(self,subject:str,predicate:str,limit:int=20): return [dict(x) for x in self.db.execute("SELECT * FROM facts WHERE subject=? AND predicate=? ORDER BY valid_from DESC LIMIT ?",(subject,predicate,limit))]
    def causal_chain(self,fact_id:str,max_hops:int=4):
        seen={fact_id}; frontier=[fact_id]; edges=[]
        for _ in range(max_hops):
            nxt=[]
            for node in frontier:
                for row in self.db.execute("SELECT * FROM causal WHERE cause_id=? OR effect_id=? ORDER BY confidence DESC",(node,node)):
                    d=dict(row); edges.append(d); other=d['effect_id'] if d['cause_id']==node else d['cause_id']
                    if other not in seen: seen.add(other); nxt.append(other)
            if not nxt: break
            frontier=nxt
        facts=[]
        for fid in seen:
            row=self.db.execute("SELECT * FROM facts WHERE id=?",(fid,)).fetchone()
            if row: facts.append(dict(row))
        return {'facts':facts,'edges':edges}
    def close(self): self.db.close()

def route(query:str)->ReasoningRoute:
    q=query.lower()
    deliberate=('pourquoi','cause','raison','après','avant','changé','historique','relation','dépend','why','because','changed','history')
    if any(x in q for x in deliberate): return ReasoningRoute('system2','causal_or_temporal_reasoning',4)
    return ReasoningRoute('system1','direct_retrieval',1)
