#!/usr/bin/env python3
"""Intent-gated, multi-view retrieval for Quantic V2 memory."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import re, time

try:
    from .qmemory2 import MemoryStore
    from .qmemory_graph import FrontierMemory
    from .qmemory_trust import citation_lock
except ImportError:
    from qmemory2 import MemoryStore
    from qmemory_graph import FrontierMemory
    from qmemory_trust import citation_lock

@dataclass(frozen=True)
class RetrievalIntent:
    self_contained: bool
    episodic: bool
    temporal: bool
    entity: bool
    documentary: bool
    procedural: bool
    reason: str

TEMPORAL = re.compile(r"\b(quand|hier|aujourd|demain|dernier|avant|apres|depuis|date|fois|when|yesterday|last|before|after)\b", re.I)
PROCEDURAL = re.compile(r"\b(comment|reprends|continuer|procedure|etapes|methode|how|resume|continue|steps|method)\b", re.I)
REFERENCE = re.compile(r"\b(ca|cela|ce qu|on faisait|notre|mon projet|souviens|rappelle|remember|that|we did|my project)\b", re.I)
DOCUMENT = re.compile(r"\b(document|fichier|rapport|note|spec|readme|doc|file|report)\b", re.I)
ENTITY = re.compile(r"\b(qui|personne|projet|repo|application|service|who|project|repository|app)\b", re.I)

def classify(query: str) -> RetrievalIntent:
    q=query.strip()
    temporal=bool(TEMPORAL.search(q)); procedural=bool(PROCEDURAL.search(q)); documentary=bool(DOCUMENT.search(q)); entity=bool(ENTITY.search(q)); ref=bool(REFERENCE.search(q))
    self_contained = len(q) > 28 and not any((temporal, procedural, documentary, entity, ref))
    episodic = temporal or ref or procedural
    return RetrievalIntent(self_contained, episodic, temporal, entity or ref, documentary, procedural, "heuristic-local-intent-gate")

def _terms(query: str) -> list[str]:
    return [x.lower() for x in re.findall(r"[\wÀ-ÿ'-]+", query) if len(x) > 2]

def _graph_for(store: MemoryStore | None) -> FrontierMemory:
    if store is not None and getattr(store, "path", None):
        return FrontierMemory(Path(store.path).with_name("qmemory_graph.sqlite3"))
    return FrontierMemory()

def _trusted_source(store: MemoryStore, memory_id: str | None) -> dict[str, Any] | None:
    if not memory_id:
        return None
    memory = store.get(str(memory_id), touch=False)
    if memory is None:
        return None
    return citation_lock(memory, for_action=True)

def retrieve(query: str, *, namespace: str="user:default", store: MemoryStore|None=None, graph: FrontierMemory|None=None, limit: int=8) -> dict[str,Any]:
    intent=classify(query)
    if intent.self_contained:
        return {"query":query,"intent":asdict(intent),"evidence":[],"abstain":False,"latency_ms":0}
    own_store=store is None
    store=store or MemoryStore()
    evidence=[]; seen=set(); terms=_terms(query); started=time.perf_counter()
    kinds=[]
    if intent.procedural: kinds.append("procedural")
    if intent.episodic: kinds.append("episodic")
    if not kinds: kinds=["semantic","user","relationship"]
    for m in store.recall(query, namespace=namespace, kinds=kinds, limit=limit):
        cited = citation_lock(m, for_action=True)
        if cited is None:
            continue
        if m["id"] in seen: continue
        seen.add(m["id"]); evidence.append({
            "view":"memory",
            "memory_id":m["id"],
            "score":m.get("score",0),
            "content":cited["content"],
            "provenance":cited["citation"],
            "confidence":cited["confidence"],
            "authority":cited["authority"],
            "authentic":cited["authentic"],
            "quarantined":cited["quarantined"],
        })

    need_graph = intent.temporal or intent.episodic or intent.documentary or intent.entity
    own_graph = graph is None and need_graph
    if need_graph:
        graph = graph or _graph_for(store)
        if intent.temporal or intent.episodic:
            for row in graph.timeline(limit=50):
                text=str(row.get("summary","")).lower(); overlap=sum(t in text for t in terms)
                if overlap or intent.temporal:
                    cited = _trusted_source(store, row.get("memory_id"))
                    if cited is None:
                        continue
                    evidence.append({
                        "view":"timeline","memory_id":row.get("memory_id"),"score":0.45+0.04*overlap,
                        "content":{"summary":row.get("summary"),"ts":row.get("ts"),"kind":row.get("kind")},
                        "provenance":cited["citation"],"confidence":min(0.75, float(cited["confidence"])),
                        "authority":cited["authority"],"authentic":cited["authentic"],"quarantined":cited["quarantined"],
                    })
        if intent.documentary:
            rows=graph.db.execute("SELECT * FROM documents ORDER BY created_at DESC LIMIT 100").fetchall()
            for row in rows:
                text=(str(row["title"])+" "+str(row["text"])).lower(); overlap=sum(t in text for t in terms)
                if overlap:
                    cited = _trusted_source(store, row["memory_id"])
                    if cited is None:
                        continue
                    evidence.append({
                        "view":"document","memory_id":row["memory_id"],"score":0.5+0.05*overlap,
                        "content":{"title":row["title"],"text":row["text"],"level":row["level"]},
                        "provenance":cited["citation"],"confidence":min(0.8, float(cited["confidence"])),
                        "authority":cited["authority"],"authentic":cited["authentic"],"quarantined":cited["quarantined"],
                    })
        if intent.entity:
            rows=graph.db.execute("SELECT * FROM entities ORDER BY updated_at DESC LIMIT 100").fetchall()
            for row in rows:
                name=str(row["canonical_name"]).lower(); overlap=sum(t in name for t in terms)
                if overlap:
                    evidence.append({
                        "view":"entity","memory_id":None,"score":0.48+0.06*overlap,
                        "content":{"id":row["id"],"name":row["canonical_name"],"type":row["entity_type"]},
                        "provenance":{"source":"knowledge_graph"},"confidence":0.75,
                        "authority":"informational_only","authentic":False,"quarantined":True,
                    })
    evidence.sort(key=lambda x:(float(x.get("score",0)),float(x.get("confidence",0))), reverse=True)
    evidence=evidence[:limit]
    if own_store: store.close()
    if own_graph and graph is not None: graph.close()
    return {"query":query,"intent":asdict(intent),"evidence":evidence,"abstain":not bool(evidence),"latency_ms":round((time.perf_counter()-started)*1000,2)}
