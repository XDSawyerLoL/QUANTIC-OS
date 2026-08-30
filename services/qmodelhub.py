#!/usr/bin/env python3
"""Q-Model Hub — hardware-aware, keyless local LLM routing for Quantic OS."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Iterable

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


@dataclass(frozen=True)
class ModelProfile:
    name: str
    roles: tuple[str, ...]
    min_context: int
    min_ram_gib: float
    preferred_vram_gib: float
    quality: int
    notes: str


# Routing hints only. Quantic never downloads a model merely because it appears here.
CATALOG: tuple[ModelProfile, ...] = (
    ModelProfile("qwen3:4b", ("chat", "tools", "coding"), 65536, 8, 4, 55,
                 "Light local text/tool tier."),
    ModelProfile("gemma3:4b", ("chat", "vision"), 65536, 8, 4, 52,
                 "Light multimodal tier."),
    ModelProfile("qwen3.8:27b", ("chat", "tools", "coding", "vision", "reasoning"), 65536, 24, 16, 90,
                 "Heavy local reasoning/tool tier; use only when hardware headroom allows."),
)


def _get_json(url: str, timeout: int = 3) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def ollama_models(host: str = OLLAMA_HOST) -> list[str]:
    try:
        data = _get_json(host + "/api/tags")
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return []
    return [m.get("name", "") for m in data.get("models", []) if m.get("name")]


def total_ram_gib() -> float:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 1024 / 1024
    except OSError:
        pass
    return 0.0


def nvidia_vram_gib() -> float:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            text=True, timeout=2, stderr=subprocess.DEVNULL,
        )
        vals = [float(x.strip()) / 1024 for x in out.splitlines() if x.strip()]
        return max(vals, default=0.0)
    except (OSError, subprocess.SubprocessError, ValueError):
        return 0.0


def normalize(name: str) -> str:
    return name.split("@", 1)[0]


def installed_profile_names(installed: Iterable[str]) -> set[str]:
    names: set[str] = set()
    for raw in installed:
        n = normalize(raw)
        names.add(n)
        if n.endswith(":latest"):
            names.add(n[:-7])
    return names


def hardware_tier(ram_gib: float | None = None, vram_gib: float | None = None) -> str:
    ram = total_ram_gib() if ram_gib is None else ram_gib
    vram = nvidia_vram_gib() if vram_gib is None else vram_gib
    if ram >= 32 and (vram >= 12 or vram == 0):
        return "max"
    if ram >= 16:
        return "balanced"
    return "light"


def _fits(profile: ModelProfile, ram: float, vram: float) -> bool:
    if ram and ram < profile.min_ram_gib:
        return False
    # VRAM is preferred, not mandatory: Ollama can CPU/RAM offload.
    return True


def choose_model(
    role: str = "chat",
    installed: Iterable[str] | None = None,
    ram_gib: float | None = None,
    vram_gib: float | None = None,
) -> str | None:
    discovered = installed is None
    installed = list(ollama_models() if discovered else installed)
    have = installed_profile_names(installed)
    # If the caller supplied an installed-model list but no hardware figures,
    # hardware is intentionally treated as unknown rather than borrowing the
    # environment running the test/call.
    ram = (total_ram_gib() if discovered else 0.0) if ram_gib is None else ram_gib
    vram = (nvidia_vram_gib() if discovered else 0.0) if vram_gib is None else vram_gib

    candidates = [p for p in CATALOG if role in p.roles and p.name in have and _fits(p, ram, vram)]
    # Prefer quality, but penalize the heavy tier if RAM is only marginal.
    candidates.sort(key=lambda p: p.quality - (20 if ram and ram < p.min_ram_gib * 1.35 else 0), reverse=True)
    if candidates:
        return candidates[0].name
    return installed[0] if installed and role == "chat" else None


def recommended_profile(ram_gib: float | None = None, vram_gib: float | None = None) -> str:
    return hardware_tier(ram_gib, vram_gib)


def status() -> dict:
    installed = ollama_models()
    ram = total_ram_gib()
    vram = nvidia_vram_gib()
    return {
        "provider": "ollama-local",
        "api_key_required": False,
        "host": OLLAMA_HOST,
        "installed_models": installed,
        "recommended_profile": recommended_profile(ram, vram),
        "selected": {
            role: choose_model(role, installed, ram, vram)
            for role in ("chat", "tools", "coding", "vision", "reasoning")
        },
        "hardware": {"ram_gib": round(ram, 1), "nvidia_vram_gib": round(vram, 1)},
        "catalog": [asdict(x) for x in CATALOG],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Quantic OS keyless local model hub")
    p.add_argument("command", nargs="?", default="status", choices=["status", "choose", "profile"])
    p.add_argument("--role", default="chat")
    args = p.parse_args()
    if args.command == "choose":
        print(choose_model(args.role) or "")
    elif args.command == "profile":
        print(recommended_profile())
    else:
        print(json.dumps(status(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
