#!/usr/bin/env python3
"""AURA Universal Bridge for Quantic OS.

Local AURA is preferred. Cloud AURA is used only when an explicit private token
is configured. Q-Agent keeps a local Ollama fallback so Quantic OS remains usable
offline.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

AURA_LOCAL_URL = os.environ.get("AURA_LOCAL_URL", "http://127.0.0.1:8787").rstrip("/")
AURA_CLOUD_URL = os.environ.get(
    "AURA_CLOUD_URL",
    "https://antiquewhite-dolphin-780448.hostingersite.com",
).rstrip("/")
AURA_CLOUD_TOKEN = os.environ.get("AURA_CLOUD_TOKEN", "").strip()
BRIDGE_VERSION = "aura-universal-bridge-v1"


def _request(url: str, payload: dict[str, Any], *, token: str = "", timeout: int = 8) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Quantic-OS/AURA-Bridge-1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw or "{}")


def register() -> bool:
    if not AURA_CLOUD_TOKEN:
        return False
    payload = {
        "id": "quantic-os",
        "name": "Quantic OS",
        "objective": "Couche système et environnement agentique local de Quantic.",
        "repository": "XDSawyerLoL/QUANTIC-OS",
        "criticality": 0.94,
        "state": "online",
        "capabilities": ["system", "local-control", "agents", "sandbox", "desktop"],
        "writable_by_aura": True,
        "modification_policy": "branch-test-canary-promote",
        "bridge_version": BRIDGE_VERSION,
        "runtime": {"local_aura": AURA_LOCAL_URL},
    }
    try:
        _request(f"{AURA_CLOUD_URL}/api/aura/products/register", payload, token=AURA_CLOUD_TOKEN)
        return True
    except Exception:
        return False


def observe(state: str = "online", detail: str = "", metadata: dict[str, Any] | None = None) -> bool:
    if not AURA_CLOUD_TOKEN:
        return False
    try:
        _request(
            f"{AURA_CLOUD_URL}/api/aura/products/quantic-os/observe",
            {"state": state, "detail": detail, "metadata": metadata or {}},
            token=AURA_CLOUD_TOKEN,
        )
        return True
    except Exception:
        return False


def event(kind: str, payload: dict[str, Any] | None = None) -> bool:
    if not AURA_CLOUD_TOKEN:
        return False
    try:
        _request(
            f"{AURA_CLOUD_URL}/api/aura/products/quantic-os/event",
            {"type": kind, "payload": payload or {}},
            token=AURA_CLOUD_TOKEN,
        )
        return True
    except Exception:
        return False


def ask_local_aura(prompt: str, *, role: str = "auto", max_tokens: int = 700) -> str:
    """Ask local AURA first. Raises when local AURA is unavailable."""
    payload = {
        "prompt": str(prompt)[:60000],
        "system_instruction": (
            "Tu es AURA intégrée à Quantic OS. Respecte les politiques système locales, "
            "n'affirme jamais qu'une action OS a été exécutée sans reçu du runtime."
        ),
        "task_role": str(role)[:80],
        "max_tokens": max(64, min(int(max_tokens), 4000)),
        "distributed": False,
        "source": "quantic-os",
    }
    data = _request(f"{AURA_LOCAL_URL}/api/ai/generate", payload, timeout=90)
    answer = str(data.get("answer") or "").strip()
    if not answer:
        raise RuntimeError("AURA locale a renvoyé une réponse vide")
    return answer
