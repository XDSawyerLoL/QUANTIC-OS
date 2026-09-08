#!/usr/bin/env python3
"""Q-Workflow Learning: learn verified multi-step procedures without expanding authority."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Callable
import hashlib, json

RISK_ORDER={"low":0,"medium":1,"high":2,"critical":3}

@dataclass(frozen=True)
class WorkflowCandidate:
    name:str
    steps:list[dict[str,Any]]
    source_receipts:list[str]
    capabilities:list[str]
    max_risk:str
    reversible:bool
    baseline_actions:int
    candidate_actions:int
    confidence:float
    digest:str

@dataclass(frozen=True)
class WorkflowEvaluation:
    accepted:bool
    reason:str
    baseline_success:float
    candidate_success:float
    baseline_actions:float
    candidate_actions:float
    improvement:float
    trials:int


def _digest(steps):
    raw=json.dumps(steps,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def build_candidate(name:str, episodes:list[dict[str,Any]], *, min_repetitions:int=3) -> WorkflowCandidate:
    """Episodes are successful ordered executions of the same task family."""
    good=[e for e in episodes if e.get("ok") is True and e.get("verified",True)]
    if len(good)<min_repetitions: raise ValueError("insufficient_verified_repetitions")
    sequences=[[dict(s) for s in e.get("steps",[])] for e in good]
    if not sequences or not sequences[0]: raise ValueError("empty_workflow")
    # Conservative core: retain only the longest common prefix. A learned optimizer may
    # propose a shorter sequence later, but observation alone never invents actions.
    core=[]
    for rows in zip(*sequences):
        sig={(r.get("tool"),json.dumps(r.get("arguments",{}),sort_keys=True)) for r in rows}
        if len(sig)!=1: break
        core.append(rows[0])
    if not core: raise ValueError("no_stable_sequence")
    caps=sorted({str(s.get("capability","unknown")) for s in core})
    risks=[str(s.get("risk","low")) for s in core]
    max_risk=max(risks,key=lambda x:RISK_ORDER.get(x,99))
    receipts=[str(e.get("receipt_id","")) for e in good if e.get("receipt_id")]
    avg=sum(len(x) for x in sequences)/len(sequences)
    conf=min(.99,.70+.05*len(good))
    return WorkflowCandidate(name,core,receipts,caps,max_risk,all(bool(s.get("reversible",False)) for s in core),round(avg),len(core),conf,_digest(core))

def evaluate_candidate(candidate:WorkflowCandidate, baseline:Callable[[],dict], proposed:Callable[[],dict], *, trials:int=5, min_success:float=.90, min_improvement:float=.05) -> WorkflowEvaluation:
    if trials<3: raise ValueError("at_least_three_trials_required")
    b=[]; p=[]
    for _ in range(trials): b.append(baseline()); p.append(proposed())
    bs=sum(bool(x.get("ok")) for x in b)/trials; ps=sum(bool(x.get("ok")) for x in p)/trials
    ba=sum(float(x.get("actions",candidate.baseline_actions)) for x in b)/trials
    pa=sum(float(x.get("actions",candidate.candidate_actions)) for x in p)/trials
    action_gain=max(0.0,(ba-pa)/max(ba,1.0)); reliability_gain=ps-bs
    improvement=.65*action_gain+.35*reliability_gain
    accepted=ps>=min_success and ps>=bs and improvement>=min_improvement
    reason="verified_improvement" if accepted else "regression_or_insufficient_gain"
    return WorkflowEvaluation(accepted,reason,bs,ps,ba,pa,improvement,trials)

def propose_compression(candidate:WorkflowCandidate, optimizer:Callable[[list[dict]],list[dict]]) -> WorkflowCandidate:
    steps=optimizer([dict(x) for x in candidate.steps])
    if not steps or len(steps)>len(candidate.steps): raise ValueError("optimizer_did_not_compress")
    old_caps=set(candidate.capabilities); new_caps={str(s.get("capability","unknown")) for s in steps}
    if not new_caps.issubset(old_caps): raise PermissionError("compression_expands_capabilities")
    old_risk=RISK_ORDER.get(candidate.max_risk,99)
    if any(RISK_ORDER.get(str(s.get("risk","low")),99)>old_risk for s in steps): raise PermissionError("compression_increases_risk")
    return WorkflowCandidate(candidate.name,steps,candidate.source_receipts,sorted(new_caps),candidate.max_risk,all(bool(s.get("reversible",False)) for s in steps),candidate.baseline_actions,len(steps),candidate.confidence,_digest(steps))

def promotion_gate(candidate:WorkflowCandidate, evaluation:WorkflowEvaluation, *, simulation_passed:bool, regression_passed:bool, approved:bool=False) -> dict[str,Any]:
    if not evaluation.accepted: return {"promote":False,"reason":"benchmark_rejected"}
    if not simulation_passed: return {"promote":False,"reason":"simulation_failed"}
    if not regression_passed: return {"promote":False,"reason":"regression_failed"}
    if RISK_ORDER.get(candidate.max_risk,99)>=RISK_ORDER["high"] and not approved: return {"promote":False,"reason":"human_approval_required"}
    return {"promote":True,"reason":"evidence_gated_promotion","candidate":asdict(candidate),"evaluation":asdict(evaluation)}
