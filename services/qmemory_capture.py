#!/usr/bin/env python3
"""Q-Memory Capture: turn verified runtime evidence into provenance-qualified memories."""
from __future__ import annotations

from typing import Any
import time

try:
    from .qcontracts import MemoryRecord, Receipt
    from .qmemory2 import MemoryStore
except ImportError:
    from qcontracts import MemoryRecord, Receipt
    from qmemory2 import MemoryStore


def _confidence(receipt: Receipt) -> float:
    runtime = receipt.evidence.get("runtime", {}) if isinstance(receipt.evidence, dict) else {}
    verification = runtime.get("verification", {}) if isinstance(runtime, dict) else {}
    if receipt.ok and verification.get("passed") is True:
        return 0.98
    if receipt.ok:
        return 0.82
    return 0.72


def capture_receipt(receipt: Receipt, *, tool: str, arguments: dict[str, Any], namespace: str | None = None,
                    capability: str = "unknown", reversible: bool = False, risk: str = "low",
                    store: MemoryStore | None = None) -> MemoryRecord:
    """Persist a compact episodic execution memory from a receipt.

    Action security metadata is retained so Q-Learning cannot accidentally
    promote a learned procedure without knowing the capability/risk observed at
    execution time. Raw secrets must still be redacted by the caller.
    """
    own_store = store is None
    store = store or MemoryStore()
    ns = namespace or f"goal:{receipt.goal_id}"
    runtime = receipt.evidence.get("runtime", {}) if isinstance(receipt.evidence, dict) else {}
    verification = runtime.get("verification", {}) if isinstance(runtime, dict) else {}
    record = MemoryRecord(
        namespace=ns,
        kind="episodic",
        content={
            "key": f"execution:{tool}",
            "tool": tool,
            "arguments": arguments,
            "capability": capability,
            "reversible": bool(reversible),
            "risk": risk,
            "outcome": "success" if receipt.ok else "failure",
            "stage": receipt.stage,
            "verification": verification,
            "error": receipt.error,
        },
        provenance={
            "type": "verified_receipt",
            "receipt_id": receipt.id,
            "action_id": receipt.action_id,
            "goal_id": receipt.goal_id,
            "captured_at": time.time(),
        },
        confidence=_confidence(receipt),
    )
    try:
        store.remember(record)
    finally:
        if own_store:
            store.close()
    return record


def capture_conversation(text: str, *, namespace: str = "user:default", source: str = "conversation",
                         confidence: float = 0.70, store: MemoryStore | None = None) -> MemoryRecord:
    """Capture a user/conversation observation as a candidate memory, not an unquestioned fact."""
    own_store = store is None
    store = store or MemoryStore()
    record = MemoryRecord(
        namespace=namespace,
        kind="working",
        content={"key": f"conversation:{int(time.time())}", "text": text},
        provenance={"type": source, "captured_at": time.time()},
        confidence=confidence,
    )
    try:
        store.remember(record)
    finally:
        if own_store:
            store.close()
    return record
