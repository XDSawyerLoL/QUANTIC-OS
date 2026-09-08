#!/usr/bin/env python3
"""Canonical Quantic V2 agent contracts.

These immutable dataclasses define the durable language shared by planner,
policy, executor, verifier, memory and UI layers.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal
import time
import uuid

Status = Literal["pending", "running", "paused", "waiting_approval", "done", "failed", "cancelled"]
Risk = Literal["low", "medium", "high", "critical"]


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass(frozen=True)
class Intent:
    text: str
    actor: str = "user"
    context: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: _id("intent"))
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class Goal:
    title: str
    intent_id: str
    success_criteria: list[str]
    budget: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: _id("goal"))
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class Action:
    tool: str
    arguments: dict[str, Any]
    capability: str
    reversible: bool = False
    risk: Risk = "low"
    id: str = field(default_factory=lambda: _id("action"))


@dataclass(frozen=True)
class Plan:
    goal_id: str
    actions: list[Action]
    strategy: str = "default"
    id: str = field(default_factory=lambda: _id("plan"))
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class Mandate:
    goal_id: str
    allowed_capabilities: list[str]
    denied_capabilities: list[str] = field(default_factory=list)
    expires_at: float | None = None
    max_actions: int | None = None
    max_risk: Risk = "medium"
    require_approval_above: Risk = "medium"
    id: str = field(default_factory=lambda: _id("mandate"))


@dataclass(frozen=True)
class Receipt:
    action_id: str
    goal_id: str
    ok: bool
    stage: str
    evidence: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    id: str = field(default_factory=lambda: _id("receipt"))
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class MemoryRecord:
    namespace: str
    kind: Literal["working", "episodic", "semantic", "procedural", "user", "relationship"]
    content: dict[str, Any]
    provenance: dict[str, Any]
    confidence: float = 1.0
    id: str = field(default_factory=lambda: _id("mem"))
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class SkillManifest:
    name: str
    version: str
    capabilities: list[str]
    permissions: list[str]
    entrypoint: str
    source: str = "local"
    trusted: bool = False
    id: str = field(default_factory=lambda: _id("skill"))


def to_dict(obj: Any) -> dict[str, Any]:
    return asdict(obj)
