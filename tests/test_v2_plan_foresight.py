from pathlib import Path

from services.qcontracts import MemoryRecord
from services.qdag_runtime import DagNode
from services.qmemory2 import MemoryStore
from services.qplan_foresight import learn_failure_stats, forecast_nodes, harden_dag, advise_plan


def _remember(store: MemoryStore, tool: str, outcome: str, idx: int) -> None:
    store.remember(MemoryRecord(
        namespace="user:default",
        kind="episodic",
        content={"tool": tool, "outcome": outcome, "key": f"exec:{tool}:{idx}"},
        provenance={"type": "verified_receipt", "receipt_id": f"r{idx}"},
        confidence=.95,
    ))


def test_learns_smoothed_failure_stats(tmp_path: Path):
    store=MemoryStore(tmp_path/"m.sqlite3")
    for i,outcome in enumerate(["failure","failure","success","failure","success"]):
        _remember(store,"fragile.tool",outcome,i)
    stats=learn_failure_stats(store=store)
    assert stats["fragile.tool"].samples==5
    assert stats["fragile.tool"].failures==3
    assert 0 < stats["fragile.tool"].posterior_failure < 1
    store.close()


def test_forecast_uses_history_and_graph_criticality(tmp_path: Path):
    store=MemoryStore(tmp_path/"m.sqlite3")
    for i,outcome in enumerate(["failure","failure","failure","success","failure"]):
        _remember(store,"fragile.tool",outcome,i)
    nodes=[
        DagNode("a",{"tool":"fragile.tool"},[],["read"],"medium"),
        DagNode("b",{"tool":"safe.tool"},["a"],["read"],"low"),
        DagNode("c",{"tool":"safe.tool"},["b"],["read"],"low"),
    ]
    forecasts=forecast_nodes(nodes,stats=learn_failure_stats(store=store),fragility_threshold=.30)
    fa=next(x for x in forecasts if x.node_id=="a")
    assert fa.fragile
    assert "historical_failures" in fa.reasons
    assert "high_downstream_impact" in fa.reasons
    store.close()


def test_hardening_inserts_capability_neutral_preflight():
    nodes=[
        DagNode("a",{"tool":"fragile.tool"},[],["read"],"medium"),
        DagNode("b",{"tool":"safe.tool"},["a"],["read"],"low"),
    ]
    from services.qplan_foresight import NodeForecast
    forecasts=[NodeForecast("a","fragile.tool",.7,8,1.0,.78,True,["historical_failures"])]
    hardened,change=harden_dag(nodes,forecasts,max_checkpoints=1)
    pre=next(n for n in hardened if n.id=="preflight::a")
    target=next(n for n in hardened if n.id=="a")
    assert pre.capabilities==[] and pre.risk=="low"
    assert target.depends_on==["preflight::a"]
    assert change["hardened_nodes"]==["a"]


def test_advise_plan_keeps_quantum_optional(tmp_path: Path):
    store=MemoryStore(tmp_path/"m.sqlite3")
    for i in range(4): _remember(store,"fragile.tool","failure",i)
    nodes=[DagNode("a",{"tool":"fragile.tool"},[],["read"],"medium")]
    out=advise_plan(nodes,store=store,fragility_threshold=.10,checkpoint_budget=1,quantum_backend_available=False)
    assert out["changes"]["inserted_checkpoints"]==["preflight::a"]
    assert out["quantum"]["use_quantum"] is False
    store.close()
