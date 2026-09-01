#!/usr/bin/env python3
"""Dependency-aware DAG replanning for Quantic V2.

Preserves verified branches, invalidates only descendants impacted by changed
assumptions or failed nodes, and resumes from the minimal affected frontier.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib, json

NodeWorker = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]

@dataclass(frozen=True)
class DagNode:
    id: str
    task: dict[str, Any]
    depends_on: list[str]
    capabilities: list[str]
    risk: str = "low"

@dataclass
class DagState:
    status: dict[str, str]
    outputs: dict[str, dict[str, Any]]
    input_digests: dict[str, str]

RISK_ORDER={"low":0,"medium":1,"high":2,"critical":3}


def _digest(value: Any) -> str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def validate_dag(nodes: Iterable[DagNode]) -> dict[str, DagNode]:
    rows=list(nodes)
    by_id={n.id:n for n in rows}
    if not rows: raise ValueError("empty_dag")
    if len(by_id)!=len(rows): raise ValueError("duplicate_node_id")
    for n in by_id.values():
        unknown=[d for d in n.depends_on if d not in by_id]
        if unknown: raise ValueError(f"unknown_dependency:{n.id}:{','.join(unknown)}")
    visiting=set(); done=set()
    def visit(nid:str):
        if nid in done: return
        if nid in visiting: raise ValueError("cycle_detected")
        visiting.add(nid)
        for dep in by_id[nid].depends_on: visit(dep)
        visiting.remove(nid); done.add(nid)
    for nid in by_id: visit(nid)
    return by_id


def descendants(nodes: dict[str,DagNode], roots: Iterable[str]) -> set[str]:
    reverse={nid:set() for nid in nodes}
    for n in nodes.values():
        for dep in n.depends_on: reverse[dep].add(n.id)
    out=set(); stack=list(roots)
    while stack:
        cur=stack.pop()
        for child in reverse.get(cur,()):
            if child not in out:
                out.add(child); stack.append(child)
    return out


def _node_context(node:DagNode,state:DagState)->dict[str,Any]:
    deps={d:state.outputs[d] for d in node.depends_on if d in state.outputs}
    return {"dependencies":deps,"dependency_digest":_digest(deps)}


def affected_frontier(nodes:dict[str,DagNode],state:DagState,changed_nodes:Iterable[str])->set[str]:
    changed=set(changed_nodes)
    unknown=changed-set(nodes)
    if unknown: raise ValueError(f"unknown_changed_nodes:{','.join(sorted(unknown))}")
    return changed | descendants(nodes,changed)


def invalidate(nodes:dict[str,DagNode],state:DagState,changed_nodes:Iterable[str])->set[str]:
    impacted=affected_frontier(nodes,state,changed_nodes)
    for nid in impacted:
        state.status[nid]="pending"
        state.outputs.pop(nid,None)
        state.input_digests.pop(nid,None)
    return impacted


def execute_dag(nodes:list[DagNode], *, worker:NodeWorker, parent_capabilities:Iterable[str],
                parent_risk_ceiling:str="medium", state:DagState|None=None, max_parallel:int=3) -> dict[str,Any]:
    graph=validate_dag(nodes)
    allowed=set(parent_capabilities)
    for n in nodes:
        if not set(n.capabilities).issubset(allowed): raise PermissionError("dag_node_expands_parent_capabilities")
        if RISK_ORDER.get(n.risk,99)>RISK_ORDER.get(parent_risk_ceiling,-1): raise PermissionError("dag_node_exceeds_parent_risk")
    state=state or DagState({n.id:"pending" for n in nodes},{},{})

    while True:
        pending=[n for n in nodes if state.status.get(n.id,"pending") in {"pending","failed"}]
        if not pending: break
        ready=[n for n in pending if all(state.status.get(d)=="done" for d in n.depends_on)]
        if not ready:
            failed=[nid for nid,s in state.status.items() if s=="failed"]
            if failed: return {"ok":False,"stage":"blocked","failed":failed,"state":asdict(state)}
            return {"ok":False,"stage":"deadlock","state":asdict(state)}

        with ThreadPoolExecutor(max_workers=max(1,min(max_parallel,len(ready)))) as pool:
            futures={}
            for n in ready:
                ctx=_node_context(n,state)
                input_digest=ctx["dependency_digest"]
                futures[pool.submit(worker,asdict(n),ctx)]=(n,input_digest)
            for fut in as_completed(futures):
                n,input_digest=futures[fut]
                try: out=fut.result()
                except Exception as exc: out={"ok":False,"error":f"{type(exc).__name__}: {exc}"}
                if bool(out.get("ok")):
                    state.status[n.id]="done"; state.outputs[n.id]=out; state.input_digests[n.id]=input_digest
                else:
                    state.status[n.id]="failed"; state.outputs[n.id]=out
                    impacted=descendants(graph,[n.id])
                    for child in impacted:
                        if state.status.get(child)=="done":
                            state.status[child]="pending"; state.outputs.pop(child,None); state.input_digests.pop(child,None)
                    return {"ok":False,"stage":"node_failure","failed":[n.id],"invalidated":sorted(impacted),"state":asdict(state)}
    return {"ok":True,"stage":"complete","state":asdict(state)}


def replan_from_change(nodes:list[DagNode], state:DagState, *, changed_nodes:Iterable[str], worker:NodeWorker,
                       parent_capabilities:Iterable[str], parent_risk_ceiling:str="medium", max_parallel:int=3)->dict[str,Any]:
    graph=validate_dag(nodes)
    impacted=invalidate(graph,state,changed_nodes)
    result=execute_dag(nodes,worker=worker,parent_capabilities=parent_capabilities,parent_risk_ceiling=parent_risk_ceiling,state=state,max_parallel=max_parallel)
    result["replanned_nodes"]=sorted(impacted)
    result["preserved_nodes"]=sorted(set(graph)-impacted)
    return result
