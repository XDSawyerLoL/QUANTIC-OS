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
    assert "beginStreamingSpeech" in impl
    assert "pushStreamingText" in impl
    assert "finishStreamingSpeech" in impl


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


def test_neural_model_is_kept_warm_between_streamed_phrases():
    service = read("services/qvoice_neural.py")
    header = read("shell/src/CompanionBridge.h")
    impl = read("shell/src/CompanionBridge.cpp")
    assert "class VoiceRuntime" in service
    assert "def serve(runtime: VoiceRuntime" in service
    assert 'parser.add_argument("--server"' in service
    assert '"type": "ready"' in service
    assert '"type": "result"' in service
    assert "self._chatterbox" in service
    assert "self._kokoro" in service
    assert "m_voiceWorker" in header
    assert "ensureNeuralWorker" in impl
    assert '"--server","--engine","auto"' in impl
    assert "m_voicePendingId" in impl


def test_chatterbox_uses_v3_and_a_stable_female_reference_when_available():
    service = read("services/qvoice_neural.py")
    assert 't3_model="v3"' in service
    assert "DEFAULT_REFERENCE" in service
    assert "QUANTIC_VOICE_REFERENCE" in service
    assert "_ensure_female_reference" in service
    assert 'kwargs["audio_prompt_path"]' in service
    assert "ff_siwis" in service


def test_shell_routes_streamed_text_to_phrase_level_speech_without_duplicate_full_answer():
    backend_cpp = read("shell/src/Backend.cpp")
    main = read("shell/qml/Main.qml")
    assert "readyReadStandardOutput" in backend_cpp
    assert 'qagentPath(),"--stream-ndjson"' in backend_cpp
    assert "emit companionDelta(delta)" in backend_cpp
    assert "onCompanionDelta" in main
    assert "pushStreamingText(text)" in main
    assert "onCompanionStreamFinished" in main
    assert "finishStreamingSpeech()" in main
