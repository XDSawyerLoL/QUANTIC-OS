#!/usr/bin/env python3
"""Q-MCP Gateway — permission-aware registry for MCP servers.

This layer does not execute arbitrary server commands. It validates declarative
server records and exposes only explicitly granted capabilities to Q-Agent.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
import json

ROOT = Path("/var/lib/quantic/connectors/mcp")


@dataclass(frozen=True)
class MCPServer:
    name: str
    transport: str
    endpoint: str
    capabilities: list[str]
    network: bool
    trusted: bool


def load(path: Path) -> MCPServer:
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    transport = str(raw.get("transport", "")).lower()
    if transport not in {"stdio", "http", "https"}:
        raise ValueError("unsupported MCP transport")
    endpoint = str(raw.get("endpoint", ""))
    caps = [str(x) for x in raw.get("capabilities", [])]
    network = transport in {"http", "https"}
    trusted = bool(raw.get("trusted", False))
    if network and not trusted:
        trusted = False
    return MCPServer(str(raw["name"]), transport, endpoint, caps, network, trusted)


def discover() -> list[MCPServer]:
    if not ROOT.exists():
        return []
    out: list[MCPServer] = []
    for p in ROOT.glob("*.json"):
        try: out.append(load(p))
        except (OSError, ValueError, KeyError, json.JSONDecodeError): continue
    return out


def authorize(server: MCPServer, capability: str, approved_network: bool = False) -> dict[str, Any]:
    if not server.trusted:
        return {"ok": False, "reason": "untrusted MCP server"}
    if capability not in server.capabilities:
        return {"ok": False, "reason": "capability not declared"}
    if server.network and not approved_network:
        return {"ok": False, "reason": "network approval required"}
    return {"ok": True, "server": asdict(server), "capability": capability}
