#!/usr/bin/env python3
"""Run Q-Dream consolidation over active memory namespaces."""
from __future__ import annotations

import json

try:
    from .qmemory2 import MemoryStore
    from .qdream import consolidate
except ImportError:
    from qmemory2 import MemoryStore
    from qdream import consolidate


def run_all() -> list[dict]:
    store = MemoryStore()
    try:
        rows = store.db.execute("SELECT DISTINCT namespace FROM memories WHERE status='active'").fetchall()
        namespaces = [str(r[0]) for r in rows]
        out = []
        for namespace in namespaces:
            result = consolidate(namespace=namespace, store=store)
            out.append({"namespace": namespace, **result.__dict__})
        return out
    finally:
        store.close()


if __name__ == "__main__":
    print(json.dumps(run_all(), ensure_ascii=False, indent=2))
