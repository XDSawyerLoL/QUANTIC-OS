#!/usr/bin/env python3
"""Q-Connectors: declarative MCP/connector registry with least-privilege scopes."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json

REGISTRY_PATH = Path("/var/lib/quantic/connectors/registry.json")

@dataclass(frozen=True)
class Connector:
    name: str
    kind: str
    endpoint: str
    capabilities: tuple[str, ...]
    network: bool = False
    enabled: bool = False
    trusted: bool = False

DEFAULTS = (
    Connector("local-files", "native", "local://files", ("file.read", "file.search"), False, True, True),
    Connector("local-system", "native", "local://system", ("system.inspect",), False, True, True),
)


def load(path: Path = REGISTRY_PATH) -> dict[str, Connector]:
    items = {c.name: c for c in DEFAULTS}
    if not path.exists():
        return items
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return items
    for row in raw.get("connectors", []):
        try:
            c = Connector(
                str(row["name"]), str(row["kind"]), str(row["endpoint"]),
                tuple(str(x) for x in row.get("capabilities", [])),
                bool(row.get("network", False)), bool(row.get("enabled", False)), bool(row.get("trusted", False)),
            )
            items[c.name] = c
        except (KeyError, TypeError, ValueError):
            continue
    return items


def allowed(name: str, capability: str, *, permit_network: bool = False) -> tuple[bool, str]:
    c = load().get(name)
    if not c:
        return False, "unknown connector"
    if not c.enabled:
        return False, "connector disabled"
    if capability not in c.capabilities:
        return False, "capability not granted"
    if c.network and not permit_network:
        return False, "network approval required"
    if c.kind == "mcp" and not c.trusted:
        return False, "untrusted MCP server"
    return True, "allowed"


def export(path: Path = REGISTRY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"connectors": [asdict(c) for c in DEFAULTS]}, indent=2), encoding="utf-8")

if __name__ == "__main__":
    print(json.dumps({k: asdict(v) for k, v in load().items()}, indent=2))
