#!/usr/bin/env python3
"""Planner-facing, intent-gated memory context for Quantic V2."""
from __future__ import annotations
from typing import Any
try:
    from .qcontracts import Goal
    from .qmemory_router import retrieve
except ImportError:
    from qcontracts import Goal
    from qmemory_router import retrieve

def context_for_goal(goal: Goal | dict[str, Any], *, store=None, graph=None, limit: int = 8) -> dict[str, Any]:
    if isinstance(goal, Goal):
        title=goal.title; goal_id=goal.id; success=goal.success_criteria
    else:
        title=str(goal.get("title","")); goal_id=str(goal.get("id","")); success=list(goal.get("success_criteria",[]))
    query=" ".join([title,*[str(x) for x in success]])
    # First search goal-local evidence, then durable user memory only if needed.
    local=retrieve(query,namespace=f"goal:{goal_id}",store=store,graph=graph,limit=limit)
    evidence=list(local["evidence"])
    if len(evidence)<limit:
        durable=retrieve(query,namespace="user:default",store=store,graph=graph,limit=limit-len(evidence))
        keys={(x.get("view"),x.get("memory_id"),str(x.get("content"))) for x in evidence}
        for item in durable["evidence"]:
            key=(item.get("view"),item.get("memory_id"),str(item.get("content")))
            if key not in keys: evidence.append(item); keys.add(key)
    evidence=sorted(evidence,key=lambda x:(float(x.get("score",0)),float(x.get("confidence",0))),reverse=True)[:limit]
    return {"query":query,"goal_id":goal_id,"intent":local["intent"],"evidence":evidence,"abstain":not bool(evidence)}
