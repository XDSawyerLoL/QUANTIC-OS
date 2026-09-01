#!/usr/bin/env python3
"""Q-Dream: background consolidation for Quantic Memory 2.

Consolidates provenance-qualified episodic traces into compact semantic or
procedural memories. It never mutates protected core code and never promotes
low-confidence observations without evidence.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json
import time

try:
    from .qcontracts import MemoryRecord
    from .qmemory2 import MemoryStore
except ImportError:
    from qcontracts import MemoryRecord
    from qmemory2 import MemoryStore

DEFAULT_DIARY = Path("/var/lib/quantic/memory/dream-diary.jsonl")


@dataclass(frozen=True)
class DreamResult:
    scanned: int
    promoted: int
    conflicts: int
    decayed: int
    created_ids: list[str]


def _append_diary(path: Path, row: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def consolidate(*, namespace: str, store: MemoryStore | None = None, min_examples: int = 2,
                decay_after_days: int = 120, diary: Path = DEFAULT_DIARY) -> DreamResult:
    own_store = store is None
    store = store or MemoryStore()
    memories = store.export_namespace(namespace)
    active_episodes = [m for m in memories if m["status"] == "active" and m["kind"] == "episodic"]

    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in active_episodes:
        key = str(m["content"].get("key", ""))
        if key:
            by_key[key].append(m)

    promoted = 0
    conflicts = 0
    created_ids: list[str] = []

    for key, group in by_key.items():
        successes = [m for m in group if m["content"].get("outcome") == "success"]
        failures = [m for m in group if m["content"].get("outcome") == "failure"]
        if successes and failures:
            conflicts += 1
        if len(successes) < min_examples:
            continue

        tool = successes[-1]["content"].get("tool")
        confidence = min(0.99, sum(float(m["confidence"]) for m in successes) / len(successes))
        record = MemoryRecord(
            namespace=namespace,
            kind="procedural",
            content={
                "key": f"procedure:{tool}",
                "tool": tool,
                "lesson": f"Verified successful procedure for {tool}",
                "successful_examples": len(successes),
                "failure_examples": len(failures),
            },
            provenance={
                "type": "q-dream",
                "source_memory_ids": [m["id"] for m in successes],
                "conflicting_failure_ids": [m["id"] for m in failures],
                "consolidated_at": time.time(),
            },
            confidence=confidence,
        )
        existing = store.recall(f"procedure {tool}", namespace=namespace, kinds=["procedural"], limit=3)
        supersedes_id = None
        for item in existing:
            if item["content"].get("key") == record.content["key"]:
                supersedes_id = item["id"]
                break
        store.remember(record, supersedes_id=supersedes_id)
        promoted += 1
        created_ids.append(record.id)
        _append_diary(diary, {"event": "promoted", "namespace": namespace, "memory_id": record.id,
                              "source_count": len(successes), "conflicts": len(failures)})

    decayed = 0
    for item in store.decay_candidates(older_than_days=decay_after_days, max_confidence=0.45):
        if item["namespace"] != namespace:
            continue
        if store.forget(item["id"]):
            decayed += 1
            _append_diary(diary, {"event": "decayed", "namespace": namespace, "memory_id": item["id"]})

    result = DreamResult(len(active_episodes), promoted, conflicts, decayed, created_ids)
    _append_diary(diary, {"event": "dream.completed", "namespace": namespace, **asdict(result)})
    if own_store:
        store.close()
    return result


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Quantic Q-Dream memory consolidation")
    ap.add_argument("namespace")
    ns = ap.parse_args()
    print(json.dumps(asdict(consolidate(namespace=ns.namespace)), ensure_ascii=False, indent=2))
