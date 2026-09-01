from pathlib import Path

from services.qvoice_neural import normalize_for_speech

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_neural_voice_normalizes_screen_text_for_speech():
    text = normalize_for_speech("**CPU** à 42% 🙂 https://example.com")
    assert "processeur" in text
    assert "http" not in text
    assert "🙂" not in text
    assert text.endswith(".")


def test_shell_uses_adaptive_neural_quality_and_keeps_piper_fallback():
    header = read("shell/src/CompanionBridge.h")
    impl = read("shell/src/CompanionBridge.cpp")
    page = read("shell/qml/pages/CompanionPage.qml")
    provision = read("scripts/provision-final-ai.sh")
    assert "voiceEngine" in header
    assert "speechChunks" in header
    assert "synthesizeNextChunk" in header
    assert "m_speechQueue" in header
    assert "neuralVoiceAvailable" in impl
    assert '"ff_siwis"' in impl
    assert '"--engine","auto"' in impl
    assert "Chatterbox Multilingual · français" in impl
    assert "Kokoro 82M · français" in impl
    assert "speakPiper(chunk)" in impl
    assert "Moteur vocal · " in page
    assert "kokoro>=0.9.4" in provision
    assert "chatterbox-tts" in provision
    assert "qvoice_neural.py" in provision


def test_voice_adapter_is_local_bounded_and_adaptive():
    service = read("services/qvoice_neural.py")
    assert "MAX_CHARS" in service
    assert 'KPipeline(lang_code="f")' in service
    assert 'DEFAULT_VOICE = "ff_siwis"' in service
    assert "ChatterboxMultilingualTTS" in service
    assert 'language_id="fr"' in service
    assert "cuda_capable" in service
    assert "choose_engine" in service
    assert "HF_HUB_DISABLE_TELEMETRY" in service
    assert "subprocess" not in service


def test_phrase_streaming_starts_before_full_answer_is_synthesized():
    impl = read("shell/src/CompanionBridge.cpp")
    assert 'split(QRegularExpression("(?<=[.!?…])\\\\s+")' in impl
    assert "m_speechQueue.takeFirst()" in impl
    assert "synthesizeNextChunk()" in impl
    assert "out.mid(0,12)" in impl
    assert "m_stopRequested" in impl


def test_agent_exposes_real_ollama_delta_streaming_for_shell_pipeline():
    agent = read("services/qagent.py")
    header = read("shell/src/Backend.h")
    assert '"stream": stream' in agent
    assert "def stream_ask(" in agent
    assert "for raw in response" in agent
    assert '"type": "delta"' in agent
    assert '"--stream-ndjson"' in agent
    assert "flush=True" in agent
    assert "companionDelta(QString text)" in header
    assert "companionStreamFinished()" in header
