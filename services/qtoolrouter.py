#!/usr/bin/env python3
"""Q-Tool Router: capability registry and deterministic tool dispatch for Quantic OS.

The router never grants authority. It only resolves a declared capability to a
registered handler. Q-Policy and Q-Simulation must approve before invocation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any
import json

Handler = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    capability: str
    category: str
    reversible: bool
    sandbox: bool
    description: str


class ToolRouter:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, Handler] = {}

    def register(self, spec: ToolSpec, handler: Handler) -> None:
        if spec.name in self._specs:
            raise ValueError(f"tool already registered: {spec.name}")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def spec(self, name: str) -> ToolSpec:
        if name not in self._specs:
            raise KeyError(f"unknown tool: {name}")
        return self._specs[name]

    def list_tools(self) -> list[dict[str, Any]]:
        return [spec.__dict__.copy() for spec in self._specs.values()]

    def invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.spec(name)
        return self._handlers[name](arguments)


def _safe_path(value: str) -> Path:
    p = Path(value).expanduser().resolve()
    denied = (Path("/proc"), Path("/sys"), Path("/dev"), Path("/boot"), Path("/efi"))
    if any(p == root or root in p.parents for root in denied):
        raise PermissionError(f"protected path: {p}")
    return p


def file_read(args: dict[str, Any]) -> dict[str, Any]:
    p = _safe_path(str(args["path"]))
    limit = min(max(int(args.get("max_bytes", 262144)), 1), 1048576)
    data = p.read_bytes()[:limit]
    return {"ok": True, "path": str(p), "content": data.decode("utf-8", errors="replace"), "truncated": p.stat().st_size > limit}


def file_search(args: dict[str, Any]) -> dict[str, Any]:
    root = _safe_path(str(args.get("root", str(Path.home()))))
    needle = str(args.get("query", "")).strip().lower()
    if not needle:
        return {"ok": True, "matches": []}
    max_results = min(max(int(args.get("max_results", 50)), 1), 200)
    matches: list[str] = []
    for p in root.rglob("*"):
        if len(matches) >= max_results:
            break
        try:
            if needle in p.name.lower():
                matches.append(str(p))
        except OSError:
            continue
    return {"ok": True, "matches": matches}


def inspect_system(_: dict[str, Any]) -> dict[str, Any]:
    info = {}
    for key, path in {
        "os_release": "/etc/os-release",
        "quantic_release": "/etc/quantic-release",
    }.items():
        try:
            info[key] = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            info[key] = "unavailable"
    return {"ok": True, "system": info}


def default_router() -> ToolRouter:
    r = ToolRouter()
    r.register(ToolSpec("file.read", "file.read", "read", True, True, "Read a local text file"), file_read)
    r.register(ToolSpec("file.search", "file.search", "inspect", True, True, "Search local filenames"), file_search)
    r.register(ToolSpec("system.inspect", "system.inspect", "inspect", True, True, "Inspect Quantic release state"), inspect_system)
    return r


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("tool", nargs="?")
    ap.add_argument("arguments", nargs="?", default="{}")
    ns = ap.parse_args()
    router = default_router()
    if ns.list:
        print(json.dumps(router.list_tools(), indent=2, ensure_ascii=False))
    elif ns.tool:
        print(json.dumps(router.invoke(ns.tool, json.loads(ns.arguments)), indent=2, ensure_ascii=False))
