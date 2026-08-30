#!/usr/bin/env python3
"""Q-Agent — local-first assistant for Quantic OS.

By default it asks Q-Model Hub to select an installed Ollama model. No API key
or cloud account is required. Privileged OS actions remain outside the LLM.
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

try:
    from .qmodelhub import choose_model
except ImportError:
    from qmodelhub import choose_model

try:
    from .qcompanion import CompanionMemory
except ImportError:
    from qcompanion import CompanionMemory

SYSTEM = """You are Q-Agent, the local companion and system agent for Quantic OS.
Be concise. Explain system actions before they are performed.
Never claim an action was executed unless the operating-system tool layer confirms it.
Prefer local/private processing. Never request an API key when a local model is available.
Take useful initiative when context and permissions justify it, but avoid repetitive or intrusive prompts.
Use persistent memory only through the trusted companion memory layer.
"""


def companion_context(memory_path: str | None = None) -> str:
    path = Path(memory_path) if memory_path else Path.home() / ".local/share/quantic/companion.db"
    try:
        mem = CompanionMemory(path)
        items = mem.list_prefix("", limit=20)
    except Exception:
        return ""
    if not items:
        return ""
    safe = {k: v for k, v in items.items() if k.startswith(("goal:", "preference:", "session:", "project:"))}
    return json.dumps(safe, ensure_ascii=False) if safe else ""


def ask(model: str, prompt: str, host: str, memory_path: str | None = None) -> str:
    memory = companion_context(memory_path)
    system = SYSTEM + ("\nLocal companion context (trusted local memory): " + memory if memory else "")
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        host.rstrip("/") + "/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.load(response)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Cannot reach local Ollama at {host}: {exc}") from exc
    return data.get("message", {}).get("content", "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Quantic OS local Q-Agent")
    parser.add_argument("--model", default="auto", help="Ollama model or 'auto'")
    parser.add_argument("--role", default="chat", choices=["chat", "tools", "coding", "vision", "reasoning"])
    parser.add_argument("--host", default="http://127.0.0.1:11434")
    parser.add_argument("--memory", default=None, help="local companion memory database")
    parser.add_argument("prompt", nargs="*")
    args = parser.parse_args()

    model = args.model
    if model == "auto":
        model = choose_model(args.role)
        if not model:
            raise SystemExit(
                "No suitable local model is installed. Run scripts/setup-local-ai.sh "
                "to install the default keyless model stack."
            )

    if args.prompt:
        print(ask(model, " ".join(args.prompt), args.host, args.memory))
        return

    print(f"Q-Agent — local model={model}. Type /quit to exit.")
    while True:
        try:
            line = input("quantic> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line in {"/quit", "/exit"}:
            break
        if line:
            print(ask(model, line, args.host, args.memory))


if __name__ == "__main__":
    main()
