#!/usr/bin/env python3
"""Quantic premium local neural voice adapter.

Adaptive engines:
- Chatterbox Multilingual V3 when explicitly installed after boot and enough free
  CUDA memory remains after the LLM.
- Kokoro-82M ONNX + ff_siwis is the immutable-ISO low-latency French path.
- The original PyTorch Kokoro pipeline remains compatible when installed.
- Piper remains the shell-level emergency fallback.

The adapter never executes arbitrary commands. It accepts bounded text and writes
one WAV to an explicit path. ``--server`` keeps the selected model loaded between
streamed phrases so speech can begin before the LLM has finished its full answer.
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
DEFAULT_KOKORO_MODEL = Path("/usr/share/quantic/models/kokoro/kokoro-v1.0.onnx")
DEFAULT_KOKORO_VOICES = Path("/usr/share/quantic/models/kokoro/voices-v1.0.bin")
DEFAULT_REFERENCE = Path.home() / ".local/share/quantic/voices/quantic-female-reference.wav"
MIN_CHATTERBOX_FREE_VRAM_GB = 4.5
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


def cuda_free_gb() -> float | None:
    try:
        import torch
        if not torch.cuda.is_available():
            return None
        free_bytes, _total_bytes = torch.cuda.mem_get_info()
        return float(free_bytes) / (1024.0 ** 3)
    except Exception:
        return None


def chatterbox_available() -> bool:
    try:
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS  # noqa: F401
        import torchaudio  # noqa: F401
        return True
    except Exception:
        return False


def kokoro_onnx_available() -> bool:
    try:
        from kokoro_onnx import Kokoro  # noqa: F401
        from misaki.espeak import EspeakG2P  # noqa: F401
        import soundfile  # noqa: F401
        return DEFAULT_KOKORO_MODEL.is_file() and DEFAULT_KOKORO_VOICES.is_file()
    except Exception:
        return False


def kokoro_torch_available() -> bool:
    try:
        from kokoro import KPipeline  # noqa: F401
        import soundfile  # noqa: F401
        import numpy  # noqa: F401
        return True
    except Exception:
        return False


def kokoro_available() -> bool:
    return kokoro_onnx_available() or kokoro_torch_available()


def choose_engine(requested: str = "auto") -> str:
    if requested in {"chatterbox", "kokoro"}:
        return requested
    free_vram = cuda_free_gb()
    chatterbox_has_headroom = free_vram is not None and free_vram >= MIN_CHATTERBOX_FREE_VRAM_GB
    if cuda_capable() and chatterbox_available() and chatterbox_has_headroom:
        return "chatterbox"
    if kokoro_available():
        return "kokoro"
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
        self._chatterbox_version = "unknown"
        self._kokoro: Any = None
        self._kokoro_g2p: Any = None
        self._kokoro_backend = "none"
        configured_reference = os.environ.get("QUANTIC_VOICE_REFERENCE", "").strip()
        configured_path = Path(configured_reference).expanduser() if configured_reference else None
        self.reference = configured_path if configured_path and configured_path.is_file() else (DEFAULT_REFERENCE if DEFAULT_REFERENCE.is_file() else None)

    def _load_chatterbox(self) -> None:
        if self._chatterbox is not None:
            return
        import torch
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS

        self._chatterbox_device = "cuda" if torch.cuda.is_available() else "cpu"
        try:
            self._chatterbox = ChatterboxMultilingualTTS.from_pretrained(device=self._chatterbox_device, t3_model="v3")
            self._chatterbox_version = "v3"
        except TypeError:
            self._chatterbox = ChatterboxMultilingualTTS.from_pretrained(device=self._chatterbox_device)
            self._chatterbox_version = "legacy"

    def _load_kokoro(self) -> None:
        if self._kokoro is not None:
            return
        if kokoro_onnx_available():
            from kokoro_onnx import Kokoro
            from misaki import espeak
            from misaki.espeak import EspeakG2P

            # Constructing the fallback ensures espeak-ng is available for French
            # words outside Misaki's lexicon. The G2P output is passed explicitly
            # to Kokoro ONNX, matching the upstream French example.
            espeak.EspeakFallback(british=False)
            self._kokoro_g2p = EspeakG2P(language="fr-fr")
            self._kokoro = Kokoro(str(DEFAULT_KOKORO_MODEL), str(DEFAULT_KOKORO_VOICES))
            self._kokoro_backend = "onnx"
            return
        from kokoro import KPipeline

        self._kokoro = KPipeline(lang_code="f")
        self._kokoro_backend = "torch"

    def _kokoro_audio(self, text: str, voice: str, speed: float) -> tuple[Any, int]:
        self._load_kokoro()
        if self._kokoro_backend == "onnx":
            phonemes, _tokens = self._kokoro_g2p(text)
            samples, sample_rate = self._kokoro.create(phonemes, voice, speed=speed, is_phonemes=True)
            return samples, int(sample_rate)
        import numpy as np

        chunks = [audio for _g, _p, audio in self._kokoro(text, voice=voice, speed=speed)]
        if not chunks:
            raise RuntimeError("no-audio")
        return np.concatenate(chunks), 24000

    def _ensure_female_reference(self) -> Path | None:
        if self.reference and self.reference.is_file():
            return self.reference
        if not kokoro_available():
            return None
        try:
            import soundfile as sf

            reference_text = "Bonjour. Je suis Quantic, votre assistante locale. Je parle avec une voix calme, naturelle, claire et posée, sans précipitation."
            samples, sample_rate = self._kokoro_audio(reference_text, DEFAULT_VOICE, 0.98)
            DEFAULT_REFERENCE.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(DEFAULT_REFERENCE), samples, sample_rate)
            self.reference = DEFAULT_REFERENCE
            return self.reference
        except Exception:
            return None

    def _fallback_to_kokoro(self) -> bool:
        if not kokoro_available():
            return False
        self.selected = "kokoro"
        self._load_kokoro()
        return True

    def warmup(self) -> dict:
        try:
            if self.selected == "chatterbox":
                reference = self._ensure_female_reference()
                if reference is None:
                    if not self._fallback_to_kokoro():
                        return {"ok": False, "selected": "none", "error": "female-reference-required"}
                else:
                    self._load_chatterbox()
            elif self.selected == "kokoro":
                self._load_kokoro()
            return {
                "ok": self.selected != "none",
                "selected": self.selected,
                "backend": self._kokoro_backend if self.selected == "kokoro" else self._chatterbox_version,
                "cuda": cuda_capable(),
                "free_vram_gb": cuda_free_gb(),
                "reference": bool(self.reference and self.reference.is_file()),
                "model_version": self._chatterbox_version if self.selected == "chatterbox" else "kokoro-v1.0",
            }
        except Exception as exc:
            if self.requested_engine == "auto" and self.selected == "chatterbox":
                try:
                    if self._fallback_to_kokoro():
                        return {"ok": True, "selected": self.selected, "backend": self._kokoro_backend, "cuda": cuda_capable(), "free_vram_gb": cuda_free_gb(), "fallback": "kokoro", "reference": False, "model_version": "kokoro-v1.0"}
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

                reference = self._ensure_female_reference()
                if reference is None:
                    if self.requested_engine == "auto" and self._fallback_to_kokoro():
                        return self.synthesize(clean, output, voice=actual_voice, speed=actual_speed)
                    return {"ok": False, "error": "female-reference-required"}
                self._load_chatterbox()
                kwargs = {"language_id": "fr", "exaggeration": 0.42, "cfg_weight": 0.32, "audio_prompt_path": str(reference)}
                wav = self._chatterbox.generate(clean, **kwargs)
                output.parent.mkdir(parents=True, exist_ok=True)
                ta.save(str(output), wav, self._chatterbox.sr)
                return {
                    "ok": True,
                    "engine": "chatterbox-multilingual-v3" if self._chatterbox_version == "v3" else "chatterbox-multilingual",
                    "device": self._chatterbox_device,
                    "sample_rate": int(self._chatterbox.sr),
                    "chars": len(clean),
                    "reference": True,
                }
            except Exception as exc:
                if self.requested_engine != "auto":
                    return {"ok": False, "error": "chatterbox-failed", "detail": f"{type(exc).__name__}: {exc}"[:240]}
                try:
                    if self._fallback_to_kokoro():
                        return self.synthesize(clean, output, voice=actual_voice, speed=actual_speed)
                except Exception:
                    pass
                return {"ok": False, "error": "chatterbox-failed", "detail": f"{type(exc).__name__}: {exc}"[:240]}

        if self.selected == "kokoro":
            try:
                import soundfile as sf

                samples, sample_rate = self._kokoro_audio(clean, actual_voice, actual_speed)
                output.parent.mkdir(parents=True, exist_ok=True)
                sf.write(str(output), samples, sample_rate)
                return {"ok": True, "engine": "kokoro-82m-onnx" if self._kokoro_backend == "onnx" else "kokoro-82m", "backend": self._kokoro_backend, "voice": actual_voice, "sample_rate": sample_rate, "chars": len(clean)}
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
    status = runtime.warmup() if warm else {"ok": runtime.selected != "none", "selected": runtime.selected, "cuda": cuda_capable(), "free_vram_gb": cuda_free_gb()}
    print(json.dumps({"type": "ready", **status}, ensure_ascii=False, separators=(",", ":")), flush=True)
    if not status.get("ok"):
        return 2
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        request: dict[str, Any] = {}
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
            request_id = int(request.get("id", 0)) if isinstance(request, dict) else 0
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
        result = {"ok": True, "selected": choose_engine(args.engine), "cuda": cuda_capable(), "free_vram_gb": cuda_free_gb(), "chatterbox": chatterbox_available(), "kokoro": kokoro_available(), "kokoro_onnx": kokoro_onnx_available()}
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
