#!/usr/bin/env python3
"""Quantic premium local neural voice adapter.

Adaptive engines:
- Chatterbox Multilingual on a capable CUDA machine for maximum naturalness,
  expressive control and French zero-shot speech.
- Kokoro-82M for low-latency local conversation, especially on CPU.
- Piper remains the shell-level emergency fallback.

The adapter never executes arbitrary commands. It accepts bounded text and writes
one WAV to an explicit path. Model caches stay local through HF_HOME.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

MAX_CHARS = 1800
DEFAULT_VOICE = "ff_siwis"
DEFAULT_HF_HOME = "/usr/share/quantic/models/hf"
os.environ.setdefault("HF_HOME", DEFAULT_HF_HOME)
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def normalize_for_speech(text: str) -> str:
    text = text.strip()[:MAX_CHARS]
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[`*_#>|~]", "", text)
    text = re.sub(r"[\U0001F300-\U0001FAFF]", "", text)
    replacements = {
        "CPU": "processeur", "GPU": "carte graphique", "RAM": "mémoire vive",
        "IA": "intelligence artificielle", "OS": "système", "Wi-Fi": "wifi", "Wi‑Fi": "wifi",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text).strip()
    if text and text[-1] not in ".!?…":
        text += "."
    return text


def cuda_capable() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def chatterbox_available() -> bool:
    try:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS  # noqa: F401
        import torchaudio  # noqa: F401
        return True
    except Exception:
        return False


def kokoro_available() -> bool:
    try:
        from kokoro import KPipeline  # noqa: F401
        import soundfile  # noqa: F401
        import numpy  # noqa: F401
        return True
    except Exception:
        return False


def choose_engine(requested: str = "auto") -> str:
    if requested in {"chatterbox", "kokoro"}:
        return requested
    # Conversation profile: quality-first on CUDA, latency-first elsewhere.
    if cuda_capable() and chatterbox_available():
        return "chatterbox"
    if kokoro_available():
        return "kokoro"
    if chatterbox_available():
        return "chatterbox"
    return "none"


def synthesize_chatterbox(text: str, output: Path, *, exaggeration: float = 0.42, cfg_weight: float = 0.38) -> dict:
    try:
        import torch
        import torchaudio as ta
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    except Exception as exc:
        return {"ok": False, "error": "chatterbox-unavailable", "detail": type(exc).__name__}
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = ChatterboxMultilingualTTS.from_pretrained(device=device)
        wav = model.generate(text, language_id="fr", exaggeration=exaggeration, cfg_weight=cfg_weight)
        output.parent.mkdir(parents=True, exist_ok=True)
        ta.save(str(output), wav, model.sr)
        return {"ok": True, "engine": "chatterbox-multilingual", "device": device, "sample_rate": int(model.sr), "chars": len(text)}
    except Exception as exc:
        return {"ok": False, "error": "chatterbox-failed", "detail": f"{type(exc).__name__}: {exc}"[:240]}


def synthesize_kokoro(text: str, output: Path, *, voice: str = DEFAULT_VOICE, speed: float = 1.03) -> dict:
    try:
        from kokoro import KPipeline
        import numpy as np
        import soundfile as sf
    except Exception as exc:
        return {"ok": False, "error": "kokoro-unavailable", "detail": type(exc).__name__}
    try:
        pipeline = KPipeline(lang_code="f")
        chunks = [audio for _g, _p, audio in pipeline(text, voice=voice, speed=speed)]
        if not chunks:
            return {"ok": False, "error": "no-audio"}
        output.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output), np.concatenate(chunks), 24000)
        return {"ok": True, "engine": "kokoro-82m", "voice": voice, "sample_rate": 24000, "chars": len(text)}
    except Exception as exc:
        return {"ok": False, "error": "kokoro-failed", "detail": f"{type(exc).__name__}: {exc}"[:240]}


def synthesize(text: str, output: Path, *, engine: str = "auto", voice: str = DEFAULT_VOICE, speed: float = 1.03) -> dict:
    clean = normalize_for_speech(text)
    if not clean:
        return {"ok": False, "error": "empty-text"}
    if not (0.82 <= speed <= 1.18):
        return {"ok": False, "error": "invalid-speed"}
    selected = choose_engine(engine)
    if selected == "chatterbox":
        result = synthesize_chatterbox(clean, output)
        if result.get("ok") or engine == "chatterbox":
            return result
        selected = "kokoro"
    if selected == "kokoro":
        return synthesize_kokoro(clean, output, voice=voice, speed=speed)
    return {"ok": False, "error": "no-neural-engine"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Quantic premium local neural voice")
    parser.add_argument("--output", required=True)
    parser.add_argument("--engine", choices=["auto", "chatterbox", "kokoro"], default="auto")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--speed", type=float, default=1.03)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--warmup", action="store_true")
    parser.add_argument("text", nargs="*")
    args = parser.parse_args()
    if args.probe:
        result = {"ok": True, "selected": choose_engine(args.engine), "cuda": cuda_capable(), "chatterbox": chatterbox_available(), "kokoro": kokoro_available()}
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    text = "Initialisation vocale Quantic." if args.warmup else " ".join(args.text)
    result = synthesize(text, Path(args.output), engine=args.engine, voice=args.voice, speed=args.speed)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
