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
from typing import Callable

try:
    from .qmodelhub import choose_model
except ImportError:
    from qmodelhub import choose_model

try:
    from .qcompanion import CompanionMemory, state_directory
except ImportError:
    from qcompanion import CompanionMemory, state_directory

SYSTEM = """Tu es Q-Agent, le compagnon local et l'agent système de Quantic OS.
Réponds en français par défaut, sauf si l'utilisateur demande explicitement une autre langue.
Ta façon de parler doit être naturelle, fluide, calme et directe, comme un véritable assistant personnel.
Privilégie des phrases courtes à moyennes, avec un rythme oral naturel. Évite le jargon inutile, les listes mécaniques et les répétitions.
N'utilise pas d'emoji, de kaomoji ni de décoration typographique dans une réponse destinée à la conversation.
Évite de lire du code, des URL ou des blocs techniques à voix haute : résume-les naturellement sauf si l'utilisateur les demande.
Sois concis, mais pas télégraphique. Une réponse ordinaire tient généralement en deux à cinq phrases.
Explique les actions système avant qu'elles ne soient effectuées.
Ne prétends jamais qu'une action a été exécutée tant que la couche d'outils du système d'exploitation ne l'a pas confirmé.
Privilégie le traitement local et privé. Ne demande jamais de clé API lorsqu'un modèle local est disponible.
Prends une initiative utile lorsque le contexte et les permissions le justifient, sans devenir répétitif ni intrusif.
Utilise la mémoire persistante uniquement par la couche de mémoire locale de confiance du compagnon.
"""


def companion_context(memory_path: str | None = None) -> str:
    path = Path(memory_path) if memory_path else state_directory() / "companion.db"
    try:
        mem = CompanionMemory(path)
        items = mem.list_prefix("", limit=20)
    except Exception:
        return ""
    if not items:
        return ""
    safe = {k: v for k, v in items.items() if k.startswith(("goal:", "preference:", "session:", "project:"))}
    return json.dumps(safe, ensure_ascii=False) if safe else ""


def _payload(model: str, prompt: str, memory_path: str | None, stream: bool) -> bytes:
    memory = companion_context(memory_path)
    system = SYSTEM + ("\nContexte local du compagnon, issu de la mémoire locale de confiance : " + memory if memory else "")
    return json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": stream,
    }).encode("utf-8")


def ask(model: str, prompt: str, host: str, memory_path: str | None = None) -> str:
    req = urllib.request.Request(host.rstrip("/") + "/api/chat", data=_payload(model, prompt, memory_path, False), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.load(response)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Impossible de joindre Ollama local sur {host} : {exc}") from exc
    return data.get("message", {}).get("content", "")


def stream_ask(model: str, prompt: str, host: str, memory_path: str | None = None, emit: Callable[[str], None] | None = None) -> str:
    """Stream Ollama chunks. Each emitted value is already-safe assistant text."""
    req = urllib.request.Request(host.rstrip("/") + "/api/chat", data=_payload(model, prompt, memory_path, True), headers={"Content-Type": "application/json"}, method="POST")
    chunks: list[str] = []
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            for raw in response:
                if not raw.strip():
                    continue
                try:
                    item = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                text = item.get("message", {}).get("content", "")
                if text:
                    chunks.append(text)
                    if emit is not None:
                        emit(text)
                if item.get("done"):
                    break
    except urllib.error.URLError as exc:
        raise SystemExit(f"Impossible de joindre Ollama local sur {host} : {exc}") from exc
    return "".join(chunks)


def _ndjson_chunk(text: str) -> None:
    print(json.dumps({"type": "delta", "text": text}, ensure_ascii=False, separators=(",", ":")), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compagnon local Q-Agent de Quantic OS")
    parser.add_argument("--model", default="auto", help="modèle Ollama ou 'auto'")
    parser.add_argument("--role", default="chat", choices=["chat", "tools", "coding", "vision", "reasoning"])
    parser.add_argument("--host", default="http://127.0.0.1:11434")
    parser.add_argument("--memory", default=None, help="base de mémoire locale du compagnon")
    parser.add_argument("--stream-ndjson", action="store_true", help="émet les deltas Ollama en NDJSON pour le shell")
    parser.add_argument("prompt", nargs="*")
    args = parser.parse_args()

    model = args.model
    if model == "auto":
        model = choose_model(args.role)
        if not model:
            raise SystemExit("Aucun modèle Ollama n'est installé. Prépare le volume USB QUANTIC-DATA puis copie un modèle Ollama existant ou installe-en un depuis la session Quantic.")

    if args.prompt:
        prompt = " ".join(args.prompt)
        if args.stream_ndjson:
            stream_ask(model, prompt, args.host, args.memory, _ndjson_chunk)
            print(json.dumps({"type": "done"}, separators=(",", ":")), flush=True)
        else:
            print(ask(model, prompt, args.host, args.memory))
        return

    print(f"Q-Agent — modèle local={model}. Tape /quit pour quitter.")
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
