#!/usr/bin/env python3
"""Planner-facing memory context for Quantic V2.

Retrieval is bounded, namespace-aware and provenance-preserving. The planner
receives evidence, not an unqualified memory blob.
"""
from __future__ import annotations

from typing import Any

try:
    from .qcontracts import Goal
    from .qmemory2 import MemoryStore
except ImportError:
    from qcontracts import Goal
    from qmemory2 import MemoryStore


def context_for_goal(goal: Goal | dict[str, Any], *, store: MemoryStore | None = None, limit: int = 8) -> dict[str, Any]:
    own_store = store is None
    store = store or MemoryStore()
    if isinstance(goal, Goal):
        title = goal.title
        goal_id = goal.id
        success = goal.success_criteria
    else:
        title = str(goal.get("title", ""))
        goal_id = str(goal.get("id", ""))
        success = list(goal.get("success_criteria", []))

    query = " ".join([title, *[str(x) for x in success]])
    candidates: list[dict[str, Any]] = []
    # Goal-local memories get priority, then durable user/default memories.
    for namespace in (f"goal:{goal_id}", "user:default"):
        for item in store.recall(query, namespace=namespace, limit=limit):
            if item["status"] != "active":
                continue
            candidates.append(item)

    candidates.sort(key=lambda x: (float(x.get("score", 0.0)), float(x.get("confidence", 0.0))), reverse=True)
    bounded = candidates[:limit]
    result = {
        "query": query,
        "goal_id": goal_id,
        "memories": [
            {
                "id": m["id"],
                "kind": m["kind"],
                "content": m["content"],
                "confidence": m["confidence"],
                "score": m.get("score", 0.0),
                "provenance": m["provenance"],
            }
            for m in bounded
        ],
    }
    if own_store:
        store.close()
    return result
