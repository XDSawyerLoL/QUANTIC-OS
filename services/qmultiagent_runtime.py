#!/usr/bin/env python3
"""Bounded multi-agent runtime for Quantic V2.

Executes independent specialist agents in parallel, retries only failed agents,
detects simple claim conflicts, aggregates evidence, and requires final
verification before reporting success. Delegation never expands the parent
capability or risk envelope.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Any, Callable, Iterable
import time

try:
    from .qskill_orchestrator import AgentSpec, DelegationPlan, RISK_ORDER
except ImportError:
    from qskill_orchestrator import AgentSpec, DelegationPlan, RISK_ORDER

Worker = Callable[[AgentSpec, dict[str, Any]], dict[str, Any]]
Verifier = Callable[[dict[str, Any]], tuple[bool, str]]


@dataclass(frozen=True)
class AgentRun:
    agent: str
    ok: bool
    attempts: int
    latency_ms: float
    output: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class TeamReceipt:
    ok: bool
    stage: str
    runs: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    aggregate: dict[str, Any]
    verification: dict[str, Any]
    retried_agents: list[str]
    failed_agents: list[str]


def _validate_agent(spec: AgentSpec, *, parent_capabilities: Iterable[str], parent_risk_ceiling: str) -> None:
    allowed=set(parent_capabilities)
    if not set(spec.capabilities).issubset(allowed):
        raise PermissionError("agent_expands_parent_capabilities")
    if RISK_ORDER.get(spec.risk_ceiling,99)>RISK_ORDER.get(parent_risk_ceiling,-1):
        raise PermissionError("agent_exceeds_parent_risk_ceiling")


def _run_one(spec: AgentSpec, task: dict[str,Any], worker: Worker) -> AgentRun:
    started=time.perf_counter()
    try:
        out=worker(spec,task)
        ok=bool(out.get("ok",False))
        err=None if ok else str(out.get("error",out.get("stage","failed")))
        return AgentRun(spec.name,ok,1,round((time.perf_counter()-started)*1000,2),out,err)
    except Exception as exc:
        return AgentRun(spec.name,False,1,round((time.perf_counter()-started)*1000,2),{},f"{type(exc).__name__}: {exc}")


def _conflicts(runs: list[AgentRun]) -> list[dict[str,Any]]:
    """Detect contradictory scalar claims sharing the same key.

    Agents can return output['claims'] as a dict. Conflicts are reported, never
    silently resolved by majority vote.
    """
    seen:dict[str,list[tuple[str,Any]]]={}
    for run in runs:
        if not run.ok: continue
        claims=run.output.get("claims",{})
        if not isinstance(claims,dict): continue
        for key,value in claims.items(): seen.setdefault(str(key),[]).append((run.agent,value))
    out=[]
    for key,items in seen.items():
        values={repr(v) for _,v in items}
        if len(values)>1: out.append({"key":key,"claims":[{"agent":a,"value":v} for a,v in items]})
    return out


def _aggregate(runs:list[AgentRun]) -> dict[str,Any]:
    evidence=[]
    for run in runs:
        if not run.ok: continue
        evidence.append({"agent":run.agent,"result":run.output.get("result"),"evidence":run.output.get("evidence",{}),"claims":run.output.get("claims",{})})
    return {"successful_agents":len(evidence),"evidence":evidence}


def execute_team(plan: DelegationPlan, tasks: list[dict[str,Any]], *, worker: Worker,
                 parent_capabilities: Iterable[str], parent_risk_ceiling: str="medium",
                 max_retries_per_agent:int=1, verifier:Verifier|None=None) -> TeamReceipt:
    if len(tasks)!=len(plan.agents):
        raise ValueError("tasks_must_match_agents")
    for spec in plan.agents:
        _validate_agent(spec,parent_capabilities=parent_capabilities,parent_risk_ceiling=parent_risk_ceiling)

    pairs=list(zip(plan.agents,tasks))
    runs_by_name:dict[str,AgentRun]={}
    workers=max(1,min(plan.max_parallel if plan.parallel else 1,len(pairs)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(_run_one,spec,task,worker):spec.name for spec,task in pairs}
        for fut in as_completed(futures): runs_by_name[futures[fut]]=fut.result()

    retried=[]
    # Targeted recovery: retry only the failed specialist, never the whole team.
    if max_retries_per_agent>0:
        for spec,task in pairs:
            run=runs_by_name[spec.name]
            if run.ok: continue
            attempts=run.attempts
            latest=run
            for _ in range(max_retries_per_agent):
                retried.append(spec.name)
                retry=_run_one(spec,task,worker)
                attempts+=1
                latest=AgentRun(retry.agent,retry.ok,attempts,run.latency_ms+retry.latency_ms,retry.output,retry.error)
                if latest.ok: break
            runs_by_name[spec.name]=latest

    runs=[runs_by_name[s.name] for s in plan.agents]
    conflicts=_conflicts(runs)
    aggregate=_aggregate(runs)
    failed=[r.agent for r in runs if not r.ok]

    if failed:
        verification={"passed":False,"reason":"specialist_failure"}
        return TeamReceipt(False,"specialist_failure",[asdict(r) for r in runs],conflicts,aggregate,verification,retried,failed)
    if conflicts:
        verification={"passed":False,"reason":"unresolved_conflict"}
        return TeamReceipt(False,"conflict",[asdict(r) for r in runs],conflicts,aggregate,verification,retried,[])

    if verifier is None:
        passed=True; reason="structural_verification_only"
    else:
        passed,reason=verifier(aggregate)
    verification={"passed":bool(passed),"reason":str(reason)}
    return TeamReceipt(bool(passed),"complete" if passed else "verify",[asdict(r) for r in runs],conflicts,aggregate,verification,retried,[])
