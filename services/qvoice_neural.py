#!/usr/bin/env python3
"""Quantic premium local neural voice adapter.

Primary engine: Kokoro-82M, French pipeline, local inference.
Fallback remains Piper in the shell bridge when this adapter is unavailable.
The adapter accepts only bounded text and writes a WAV to an explicit path.
"""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

MAX_CHARS = 1800
DEFAULT_VOICE = "ff_siwis"
DEFAULT_HF_HOME = "/usr/share/quantic/models/hf"
os.environ.setdefault("HF_HOME", DEFAULT_HF_HOME)
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def normalize_for_speech(text: str) -> str:
    text = text.strip()[:MAX_CHARS]
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[`*_#>|~]", "", text)
    text = re.sub(r"[\U0001F300-\U0001FAFF]", "", text)
    replacements = {
        "CPU": "processeur",
        "GPU": "carte graphique",
        "RAM": "mémoire vive",
        "IA": "intelligence artificielle",
        "OS": "système",
        "Wi-Fi": "wifi",
        "Wi‑Fi": "wifi",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text).strip()
    if text and text[-1] not in ".!?…":
        text += "."
    return text


def synthesize(text: str, output: Path, *, voice: str = DEFAULT_VOICE, speed: float = 1.03) -> dict:
    clean = normalize_for_speech(text)
    if not clean:
        return {"ok": False, "error": "empty-text"}
    if not (0.82 <= speed <= 1.18):
        return {"ok": False, "error": "invalid-speed"}

    try:
        from kokoro import KPipeline
        import numpy as np
        import soundfile as sf
    except Exception as exc:
        return {"ok": False, "error": "kokoro-unavailable", "detail": type(exc).__name__}

    try:
        pipeline = KPipeline(lang_code="f")
        chunks = []
        for _graphemes, _phonemes, audio in pipeline(clean, voice=voice, speed=speed):
            chunks.append(audio)
        if not chunks:
            return {"ok": False, "error": "no-audio"}
        data = np.concatenate(chunks)
        output.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output), data, 24000)
        return {"ok": True, "engine": "kokoro-82m", "voice": voice, "sample_rate": 24000, "chars": len(clean)}
    except Exception as exc:
        return {"ok": False, "error": "kokoro-failed", "detail": f"{type(exc).__name__}: {exc}"[:240]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Quantic premium local neural voice")
    parser.add_argument("--output", required=True)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--speed", type=float, default=1.03)
    parser.add_argument("--warmup", action="store_true")
    parser.add_argument("text", nargs="*")
    args = parser.parse_args()

    text = "Initialisation vocale Quantic." if args.warmup else " ".join(args.text)
    result = synthesize(text, Path(args.output), voice=args.voice, speed=args.speed)
    import json
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
