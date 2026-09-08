#!/usr/bin/env python3
"""Q-Memory Graph: timeline + knowledge graph + hierarchical documentary memory."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json, sqlite3, time, uuid

DEFAULT_DB = Path("/var/lib/quantic/memory/qmemory_graph.sqlite3")

def _id(p: str) -> str: return f"{p}_{uuid.uuid4().hex}"

class FrontierMemory:
    def __init__(self, path: Path = DEFAULT_DB):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path); self.db.row_factory = sqlite3.Row; self._init()
    def _init(self):
        self.db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS timeline(id TEXT PRIMARY KEY, ts REAL, kind TEXT, summary TEXT, memory_id TEXT, provenance_json TEXT);
        CREATE INDEX IF NOT EXISTS idx_timeline_ts ON timeline(ts DESC);
        CREATE TABLE IF NOT EXISTS entities(id TEXT PRIMARY KEY, canonical_name TEXT, entity_type TEXT, attributes_json TEXT, updated_at REAL);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_name_type ON entities(canonical_name, entity_type);
        CREATE TABLE IF NOT EXISTS edges(id TEXT PRIMARY KEY, src TEXT, relation TEXT, dst TEXT, confidence REAL, memory_id TEXT, provenance_json TEXT, created_at REAL);
        CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src, relation);
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, parent_id TEXT, title TEXT, level INTEGER, text TEXT, memory_id TEXT, provenance_json TEXT, created_at REAL);
        CREATE INDEX IF NOT EXISTS idx_docs_parent ON documents(parent_id, level);
        """); self.db.commit()
    def add_timeline(self, kind: str, summary: str, *, memory_id: str, provenance: dict[str,Any], ts: float|None=None):
        eid=_id("time"); self.db.execute("INSERT INTO timeline VALUES(?,?,?,?,?,?)",(eid,ts or time.time(),kind,summary,memory_id,json.dumps(provenance,ensure_ascii=False))); self.db.commit(); return eid
    def upsert_entity(self, name: str, entity_type: str="concept", attributes: dict[str,Any]|None=None):
        now=time.time(); row=self.db.execute("SELECT id FROM entities WHERE canonical_name=? AND entity_type=?",(name,entity_type)).fetchone()
        if row:
            self.db.execute("UPDATE entities SET attributes_json=?,updated_at=? WHERE id=?",(json.dumps(attributes or {},ensure_ascii=False),now,row["id"])); eid=row["id"]
        else:
            eid=_id("ent"); self.db.execute("INSERT INTO entities VALUES(?,?,?,?,?)",(eid,name,entity_type,json.dumps(attributes or {},ensure_ascii=False),now))
        self.db.commit(); return eid
    def link(self, src: str, relation: str, dst: str, *, confidence: float, memory_id: str, provenance: dict[str,Any]):
        eid=_id("edge"); self.db.execute("INSERT INTO edges VALUES(?,?,?,?,?,?,?,?)",(eid,src,relation,dst,max(0,min(1,confidence)),memory_id,json.dumps(provenance,ensure_ascii=False),time.time())); self.db.commit(); return eid
    def add_document(self, title: str, text: str, *, memory_id: str, provenance: dict[str,Any], parent_id: str|None=None, level: int=0):
        did=_id("doc"); self.db.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?)",(did,parent_id,title,level,text,memory_id,json.dumps(provenance,ensure_ascii=False),time.time())); self.db.commit(); return did
    def timeline(self, limit:int=20): return [dict(x) for x in self.db.execute("SELECT * FROM timeline ORDER BY ts DESC LIMIT ?",(limit,))]
    def neighbors(self, entity_id:str, limit:int=30): return [dict(x) for x in self.db.execute("SELECT * FROM edges WHERE src=? OR dst=? ORDER BY confidence DESC LIMIT ?",(entity_id,entity_id,limit))]
    def document_children(self,parent_id:str|None=None):
        if parent_id is None: rows=self.db.execute("SELECT * FROM documents WHERE parent_id IS NULL ORDER BY created_at")
        else: rows=self.db.execute("SELECT * FROM documents WHERE parent_id=? ORDER BY created_at",(parent_id,))
        return [dict(x) for x in rows]
    def close(self): self.db.close()
