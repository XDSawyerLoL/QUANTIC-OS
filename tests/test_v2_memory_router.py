from pathlib import Path
from services.qmemory_router import classify, retrieve
from services.qmemory2 import MemoryStore
from services.qmemory_graph import FrontierMemory
from services.qcontracts import MemoryRecord

def test_self_contained_gate_skips_memory():
    x=classify("Calcule la somme de 18 et 24 puis donne uniquement le resultat numerique")
    assert x.self_contained

def test_reference_routes_to_episodic_and_entity():
    x=classify("Reprends ce qu'on faisait sur mon projet")
    assert x.episodic and x.entity and x.procedural

def test_fused_retrieval_and_abstention(tmp_path: Path):
    store=MemoryStore(tmp_path/"m.sqlite3"); graph=FrontierMemory(tmp_path/"g.sqlite3")
    rec=MemoryRecord(namespace="user:default",kind="episodic",content={"summary":"Quantic benchmark OpenClaw"},provenance={"source":"test"},confidence=.9)
    store.remember(rec); graph.add_timeline("work","Quantic benchmark OpenClaw",memory_id=rec.id,provenance={"source":"test"})
    out=retrieve("reprends le dernier benchmark Quantic",store=store,graph=graph)
    assert out["evidence"]
    assert {e["view"] for e in out["evidence"]} & {"memory","timeline"}
    store.close(); graph.close()
