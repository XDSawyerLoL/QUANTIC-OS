#!/usr/bin/env python3
"""Quantic premium local neural voice adapter.

Adaptive engines:
- Chatterbox Multilingual on a capable CUDA machine for maximum naturalness,
  expressive control and French zero-shot speech.
- Kokoro-82M for low-latency local conversation, especially on CPU.
- Piper remains the shell-level emergency fallback.

The adapter never executes arbitrary commands. It accepts bounded text and writes
one WAV to an explicit path. Model caches stay local through HF_HOME.

For conversation, ``--server`` keeps the selected neural model loaded and accepts
newline-delimited JSON synthesis requests on stdin. This removes model reload time
between spoken phrases while preserving the one-shot CLI for diagnostics/tests.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

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
    if cuda_capable() and chatterbox_available():
        return "chatterbox"
    if kokoro_available():
        return "kokoro"
    if chatterbox_available():
        return "chatterbox"
    return "none"


class VoiceRuntime:
    """One process, one warm model, many bounded synthesis requests."""

    def __init__(self, *, engine: str = "auto", voice: str = DEFAULT_VOICE, speed: float = 1.03):
        self.requested_engine = engine
        self.selected = choose_engine(engine)
        self.voice = voice
        self.speed = speed
        self._chatterbox: Any = None
        self._chatterbox_device = "cpu"
        self._kokoro: Any = None

    def _load_chatterbox(self) -> None:
        if self._chatterbox is not None:
            return
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        self._chatterbox_device = "cuda" if torch.cuda.is_available() else "cpu"
        self._chatterbox = ChatterboxMultilingualTTS.from_pretrained(device=self._chatterbox_device)

    def _load_kokoro(self) -> None:
        if self._kokoro is not None:
            return
        from kokoro import KPipeline

        self._kokoro = KPipeline(lang_code="f")

    def warmup(self) -> dict:
        try:
            if self.selected == "chatterbox":
                self._load_chatterbox()
            elif self.selected == "kokoro":
                self._load_kokoro()
            return {"ok": self.selected != "none", "selected": self.selected, "cuda": cuda_capable()}
        except Exception as exc:
            if self.requested_engine == "auto" and self.selected == "chatterbox" and kokoro_available():
                self.selected = "kokoro"
                try:
                    self._load_kokoro()
                    return {"ok": True, "selected": self.selected, "cuda": cuda_capable(), "fallback": "kokoro"}
                except Exception:
                    pass
            return {"ok": False, "selected": self.selected, "error": f"{type(exc).__name__}: {exc}"[:240]}

    def synthesize(self, text: str, output: Path, *, voice: str | None = None, speed: float | None = None) -> dict:
        clean = normalize_for_speech(text)
        if not clean:
            return {"ok": False, "error": "empty-text"}
        actual_speed = self.speed if speed is None else speed
        actual_voice = voice or self.voice
        if not (0.82 <= actual_speed <= 1.18):
            return {"ok": False, "error": "invalid-speed"}
        if self.selected == "none":
            return {"ok": False, "error": "no-neural-engine"}

        if self.selected == "chatterbox":
            try:
                import torchaudio as ta

                self._load_chatterbox()
                wav = self._chatterbox.generate(clean, language_id="fr", exaggeration=0.42, cfg_weight=0.38)
                output.parent.mkdir(parents=True, exist_ok=True)
                ta.save(str(output), wav, self._chatterbox.sr)
                return {"ok": True, "engine": "chatterbox-multilingual", "device": self._chatterbox_device, "sample_rate": int(self._chatterbox.sr), "chars": len(clean)}
            except Exception as exc:
                if self.requested_engine != "auto" or not kokoro_available():
                    return {"ok": False, "error": "chatterbox-failed", "detail": f"{type(exc).__name__}: {exc}"[:240]}
                self.selected = "kokoro"

        if self.selected == "kokoro":
            try:
                import numpy as np
                import soundfile as sf

                self._load_kokoro()
                chunks = [audio for _g, _p, audio in self._kokoro(clean, voice=actual_voice, speed=actual_speed)]
                if not chunks:
                    return {"ok": False, "error": "no-audio"}
                output.parent.mkdir(parents=True, exist_ok=True)
                sf.write(str(output), np.concatenate(chunks), 24000)
                return {"ok": True, "engine": "kokoro-82m", "voice": actual_voice, "sample_rate": 24000, "chars": len(clean)}
            except Exception as exc:
                return {"ok": False, "error": "kokoro-failed", "detail": f"{type(exc).__name__}: {exc}"[:240]}

        return {"ok": False, "error": "no-neural-engine"}


def synthesize_chatterbox(text: str, output: Path, *, exaggeration: float = 0.42, cfg_weight: float = 0.38) -> dict:
    del exaggeration, cfg_weight
    return VoiceRuntime(engine="chatterbox").synthesize(text, output)


def synthesize_kokoro(text: str, output: Path, *, voice: str = DEFAULT_VOICE, speed: float = 1.03) -> dict:
    return VoiceRuntime(engine="kokoro", voice=voice, speed=speed).synthesize(text, output)


def synthesize(text: str, output: Path, *, engine: str = "auto", voice: str = DEFAULT_VOICE, speed: float = 1.03) -> dict:
    return VoiceRuntime(engine=engine, voice=voice, speed=speed).synthesize(text, output)


def serve(runtime: VoiceRuntime, *, warm: bool = True) -> int:
    status = runtime.warmup() if warm else {"ok": runtime.selected != "none", "selected": runtime.selected, "cuda": cuda_capable()}
    print(json.dumps({"type": "ready", **status}, ensure_ascii=False, separators=(",", ":")), flush=True)
    if not status.get("ok"):
        return 2
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            request = json.loads(raw)
            request_id = int(request.get("id", 0))
            output_text = str(request.get("output", ""))
            if not output_text:
                raise ValueError("missing-output")
            text = str(request.get("text", ""))[:MAX_CHARS]
            voice = str(request.get("voice", runtime.voice))[:80]
            speed = float(request.get("speed", runtime.speed))
            result = runtime.synthesize(text, Path(output_text), voice=voice, speed=speed)
        except Exception as exc:
            request_id = int(request.get("id", 0)) if isinstance(locals().get("request"), dict) else 0
            result = {"ok": False, "error": "invalid-request", "detail": f"{type(exc).__name__}: {exc}"[:200]}
        print(json.dumps({"type": "result", "id": request_id, **result}, ensure_ascii=False, separators=(",", ":")), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Quantic premium local neural voice")
    parser.add_argument("--output")
    parser.add_argument("--engine", choices=["auto", "chatterbox", "kokoro"], default="auto")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--speed", type=float, default=1.03)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--warmup", action="store_true")
    parser.add_argument("--server", action="store_true")
    parser.add_argument("text", nargs="*")
    args = parser.parse_args()
    if args.probe:
        result = {"ok": True, "selected": choose_engine(args.engine), "cuda": cuda_capable(), "chatterbox": chatterbox_available(), "kokoro": kokoro_available()}
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    runtime = VoiceRuntime(engine=args.engine, voice=args.voice, speed=args.speed)
    if args.server:
        return serve(runtime, warm=True)
    if not args.output:
        parser.error("--output est requis hors mode --server")
    text = "Initialisation vocale Quantic." if args.warmup else " ".join(args.text)
    result = runtime.synthesize(text, Path(args.output))
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
