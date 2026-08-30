#!/usr/bin/env python3
"""Q-Permission Broker — simple capability policy for autonomous Quantic actions."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Permission(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


DEFAULT_POLICY = {
    # Safe local maintenance / reversible optimizations.
    "resource.optimize": Permission.ALLOW,
    "resource.rebalance": Permission.ALLOW,
    "cache.maintain": Permission.ALLOW,
    "security.isolate_suspicious_process": Permission.ALLOW,
    "update.noncritical_reversible": Permission.ALLOW,
    "notify.local": Permission.ALLOW,
    # User-impacting actions need consent.
    "files.delete_user_data": Permission.ASK,
    "files.move_outside_workspace": Permission.ASK,
    "messages.send_external": Permission.ASK,
    "purchase": Permission.ASK,
    "credentials.change": Permission.ASK,
    "camera.enable": Permission.ASK,
    "microphone.enable": Permission.ASK,
    # Never autonomous from a model.
    "security.disable": Permission.DENY,
    "update.bypass_guardian": Permission.DENY,
    "boot.disable_rollback": Permission.DENY,
}


@dataclass(frozen=True)
class Decision:
    capability: str
    permission: Permission
    reason: str


def decide(capability: str, overrides: dict[str, str] | None = None) -> Decision:
    policy = dict(DEFAULT_POLICY)
    for key, value in (overrides or {}).items():
        try:
            policy[key] = Permission(value)
        except ValueError:
            continue
    permission = policy.get(capability, Permission.ASK)
    reason = {
        Permission.ALLOW: "safe/reversible capability approved by local policy",
        Permission.ASK: "action may affect the user or external world",
        Permission.DENY: "capability is prohibited from autonomous execution",
    }[permission]
    return Decision(capability, permission, reason)
