#!/usr/bin/env python3
"""Q-Skill Orchestrator for Quantic V2.

Selects between reusing, evolving or creating a skill from measured evidence.
It can decompose work across bounded specialist agents, but delegation never
expands capabilities beyond the parent mandate.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Iterable
import math, re

RISK_ORDER={"low":0,"medium":1,"high":2,"critical":3}

@dataclass(frozen=True)
class SkillProfile:
    name:str
    version:str
    capabilities:list[str]
    keywords:list[str]
    success_rate:float=.5
    samples:int=0
    latency_ms:float=0.0
    risk:str="low"
    trusted:bool=True
    source:str="local"

@dataclass(frozen=True)
class SkillDecision:
    mode:str  # reuse | evolve | create | none
    skill_name:str|None
    score:float
    reason:str
    evidence:dict[str,Any]

@dataclass(frozen=True)
class AgentSpec:
    name:str
    role:str
    capabilities:list[str]
    budget_actions:int
    risk_ceiling:str="medium"

@dataclass(frozen=True)
class DelegationPlan:
    agents:list[AgentSpec]
    parallel:bool
    max_parallel:int
    reason:str


def _tokens(text:str)->set[str]:
    return {x.lower() for x in re.findall(r"[\wÀ-ÿ'-]+",text) if len(x)>2}

def score_skill(query:str, skill:SkillProfile, *, required_capabilities:Iterable[str]=())->float:
    if not skill.trusted:
        return 0.0
    required=set(required_capabilities)
    caps=set(skill.capabilities)
    if not required.issubset(caps):
        return 0.0
    q=_tokens(query); k={x.lower() for x in skill.keywords}
    lexical=len(q&k)/max(len(q|k),1)
    reliability=max(0.0,min(1.0,skill.success_rate))
    evidence=min(1.0,math.log2(max(skill.samples,1)+1)/5.0)
    latency=1.0/(1.0+max(0.0,skill.latency_ms)/2000.0)
    return round(.45*lexical+.35*reliability+.12*evidence+.08*latency,6)

def choose_skill(query:str, skills:Iterable[SkillProfile], *, required_capabilities:Iterable[str]=(), reuse_threshold:float=.55, evolve_threshold:float=.30, min_evidence:int=3)->SkillDecision:
    ranked=[]
    for skill in skills:
        s=score_skill(query,skill,required_capabilities=required_capabilities)
        if s>0: ranked.append((s,skill))
    ranked.sort(key=lambda x:x[0],reverse=True)
    if not ranked:
        return SkillDecision("create",None,0.0,"no_compatible_skill",{"candidates":0})
    score,best=ranked[0]
    ev={"samples":best.samples,"success_rate":best.success_rate,"latency_ms":best.latency_ms,"version":best.version}
    if score>=reuse_threshold and best.samples>=min_evidence:
        return SkillDecision("reuse",best.name,score,"measured_fit",ev)
    if score>=evolve_threshold and best.samples>=min_evidence:
        return SkillDecision("evolve",best.name,score,"partial_fit_with_evidence",ev)
    return SkillDecision("create",best.name,score,"insufficient_fit",ev)

def should_multi_agent(*, subtasks:int, independent_subtasks:int, estimated_actions:int, max_agents:int=4)->bool:
    return max_agents>1 and subtasks>=2 and independent_subtasks>=2 and estimated_actions>=4

def build_delegation(subtasks:list[dict[str,Any]], *, parent_capabilities:Iterable[str], max_agents:int=4, max_parallel:int=3, per_agent_budget:int=8, parent_risk_ceiling:str="medium")->DelegationPlan:
    allowed=set(parent_capabilities)
    agents=[]
    for i,task in enumerate(subtasks[:max_agents]):
        requested=set(task.get("capabilities",[]))
        if not requested.issubset(allowed):
            raise PermissionError("delegation_expands_parent_capabilities")
        risk=str(task.get("risk","low"))
        if RISK_ORDER.get(risk,99)>RISK_ORDER.get(parent_risk_ceiling,-1):
            raise PermissionError("delegation_exceeds_parent_risk_ceiling")
        agents.append(AgentSpec(
            name=str(task.get("agent",f"specialist-{i+1}")),
            role=str(task.get("role",task.get("title",f"subtask-{i+1}"))),
            capabilities=sorted(requested),
            budget_actions=max(1,min(int(task.get("budget_actions",per_agent_budget)),per_agent_budget)),
            risk_ceiling=risk,
        ))
    parallel=len(agents)>=2 and bool(all(task.get("independent",False) for task in subtasks[:len(agents)]))
    return DelegationPlan(agents,parallel,min(max_parallel,len(agents)) if parallel else 1,"bounded_specialist_delegation")

def orchestrate(query:str, skills:Iterable[SkillProfile], subtasks:list[dict[str,Any]], *, required_capabilities:Iterable[str], parent_capabilities:Iterable[str], estimated_actions:int, max_agents:int=4)->dict[str,Any]:
    decision=choose_skill(query,skills,required_capabilities=required_capabilities)
    independent=sum(bool(x.get("independent",False)) for x in subtasks)
    use_agents=should_multi_agent(subtasks=len(subtasks),independent_subtasks=independent,estimated_actions=estimated_actions,max_agents=max_agents)
    delegation=build_delegation(subtasks,parent_capabilities=parent_capabilities,max_agents=max_agents) if use_agents else DelegationPlan([],False,1,"single_agent_preferred")
    return {"skill":asdict(decision),"delegation":asdict(delegation),"use_multi_agent":use_agents}
