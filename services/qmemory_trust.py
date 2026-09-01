#!/usr/bin/env python3
"""Q-Memory Trust: origin-bound authority, quarantine and citation lock.

Memory can inform planning but never grant capabilities. Authority is bound at
write time to origin metadata and protected with an HMAC when a local key is
available. Untrusted/external memories are quarantined for action-authorizing
contexts. Dependency-free by design for the live OS.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib
import hmac
import json
import os
import time

KEY_PATH = Path("/var/lib/quantic/keys/memory-auth.key")
TRUSTED_ORIGINS = {"user_explicit", "quantic_verified", "system_policy", "signed_connector"}
UNTRUSTED_ORIGINS = {"web", "document", "message", "tool_output", "imported", "unknown"}
AUTHORITY_FIELDS = {"allow", "allowed_capabilities", "permission", "permissions", "mandate", "policy", "system_instruction", "sudo", "approve", "approved"}

@dataclass(frozen=True)
class TrustEnvelope:
    origin: str
    source_id: str
    writer: str
    authority: str
    written_at: float
    digest: str
    signature: str | None
    quarantined: bool
    reason: str = ""


def _canonical(content: dict[str, Any], origin: str, source_id: str, writer: str, written_at: float) -> bytes:
    return json.dumps({"content": content, "origin": origin, "source_id": source_id, "writer": writer, "written_at": written_at}, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _key(create: bool = False) -> bytes | None:
    try:
        if KEY_PATH.exists(): return KEY_PATH.read_bytes()
        if not create: return None
        KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        raw = os.urandom(32)
        fd = os.open(KEY_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f: f.write(raw)
        return raw
    except OSError:
        return None


def contains_authority_claim(content: dict[str, Any]) -> bool:
    def walk(value: Any, key: str = "") -> bool:
        if key.lower() in AUTHORITY_FIELDS: return True
        if isinstance(value, dict): return any(walk(v, str(k)) for k, v in value.items())
        if isinstance(value, list): return any(walk(v) for v in value)
        return False
    return walk(content)


def seal(content: dict[str, Any], *, origin: str, source_id: str, writer: str = "quantic") -> TrustEnvelope:
    ts = time.time()
    payload = _canonical(content, origin, source_id, writer, ts)
    digest = hashlib.sha256(payload).hexdigest()
    key = _key(create=True)
    signature = hmac.new(key, payload, hashlib.sha256).hexdigest() if key else None
    trusted = origin in TRUSTED_ORIGINS
    authority_claim = contains_authority_claim(content)
    quarantined = (origin in UNTRUSTED_ORIGINS or not trusted) and authority_claim
    reason = "untrusted memory attempted to carry authority" if quarantined else ""
    return TrustEnvelope(origin, source_id, writer, "informational", ts, digest, signature, quarantined, reason)


def verify(content: dict[str, Any], envelope: dict[str, Any]) -> bool:
    try:
        payload = _canonical(content, envelope["origin"], envelope["source_id"], envelope["writer"], float(envelope["written_at"]))
        if not hmac.compare_digest(hashlib.sha256(payload).hexdigest(), envelope["digest"]): return False
        key = _key(False)
        sig = envelope.get("signature")
        if key is None or not sig: return False
        return hmac.compare_digest(hmac.new(key, payload, hashlib.sha256).hexdigest(), sig)
    except (KeyError, TypeError, ValueError):
        return False


def citation_lock(memory: dict[str, Any], *, for_action: bool = False) -> dict[str, Any] | None:
    """Return bounded cited context or reject it for action-authorizing use."""
    prov = memory.get("provenance") or {}
    trust = prov.get("trust") or {}
    content = memory.get("content") or {}
    authentic = verify(content, trust) if trust else False
    quarantined = bool(trust.get("quarantined", True))
    if for_action and (not authentic or quarantined or contains_authority_claim(content)):
        return None
    return {
        "memory_id": memory.get("id"),
        "content": content,
        "citation": {"origin": trust.get("origin", prov.get("origin", "unknown")), "source_id": trust.get("source_id", prov.get("source_id", "unknown")), "digest": trust.get("digest")},
        "confidence": memory.get("confidence", 0.0),
        "authority": "informational_only",
        "authentic": authentic,
        "quarantined": quarantined,
    }


def provenance_with_trust(provenance: dict[str, Any], content: dict[str, Any], *, origin: str, source_id: str, writer: str = "quantic") -> dict[str, Any]:
    out = dict(provenance)
    out["origin"] = origin
    out["source_id"] = source_id
    out["trust"] = asdict(seal(content, origin=origin, source_id=source_id, writer=writer))
    return out
