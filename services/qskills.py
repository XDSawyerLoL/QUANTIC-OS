#!/usr/bin/env python3
"""Q-Skills — declarative skill manifests with capability boundaries."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import hashlib, json

SYSTEM_ROOT = Path("/usr/share/quantic/skills")
USER_ROOT = Path("/var/lib/quantic/skills")


@dataclass(frozen=True)
class Skill:
    name: str
    version: str
    tools: list[str]
    capabilities: list[str]
    entrypoint: str
    digest: str
    trusted: bool


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: Path) -> Skill:
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    entry = (path.parent / raw["entrypoint"]).resolve()
    trusted_root = any(root == path.parent or root in path.parents for root in (SYSTEM_ROOT, USER_ROOT))
    expected = str(raw.get("sha256", ""))
    actual = _digest(entry) if entry.is_file() else ""
    trusted = trusted_root and bool(expected) and expected == actual
    return Skill(
        str(raw["name"]), str(raw.get("version", "0")), list(raw.get("tools", [])),
        list(raw.get("capabilities", [])), str(entry), actual, trusted
    )


def discover() -> list[Skill]:
    out: list[Skill] = []
    for root in (SYSTEM_ROOT, USER_ROOT):
        if not root.exists():
            continue
        for manifest in root.rglob("skill.json"):
            try: out.append(load_manifest(manifest))
            except (OSError, ValueError, KeyError, json.JSONDecodeError): continue
    return out


def export_registry() -> list[dict[str, Any]]:
    return [asdict(s) for s in discover()]
