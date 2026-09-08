#!/usr/bin/env bash
set -euo pipefail

ROOT_TREE=${1:?Usage: provision-final-ai.sh ROOT_TREE WORKDIR}
WORK=${2:?Usage: provision-final-ai.sh ROOT_TREE WORKDIR}
MODEL_DIR="$ROOT_TREE/usr/share/quantic/models"
KOKORO_DIR="$MODEL_DIR/kokoro"
RESOLV_DST="$ROOT_TREE/etc/resolv.conf"
RESOLV_BACKUP="$WORK/resolv.conf.root-tree.backup"
HAD_RESOLV=0

sudo mkdir -p "$MODEL_DIR" "$KOKORO_DIR" "$WORK"

restore_resolver() {
  if [[ "$HAD_RESOLV" == 1 && -f "$RESOLV_BACKUP" ]]; then sudo cp -L "$RESOLV_BACKUP" "$RESOLV_DST" || true; else sudo rm -f "$RESOLV_DST" || true; fi
  return 0
}
cleanup() { local rc=$?; trap - EXIT; restore_resolver || true; exit "$rc"; }
trap cleanup EXIT

if [[ -e "$RESOLV_DST" || -L "$RESOLV_DST" ]]; then
  if sudo cp -L "$RESOLV_DST" "$RESOLV_BACKUP" 2>/dev/null; then HAD_RESOLV=1; else HAD_RESOLV=0; sudo rm -f "$RESOLV_BACKUP" || true; fi
fi
sudo rm -f "$RESOLV_DST"
sudo cp -L /etc/resolv.conf "$RESOLV_DST"
sudo chmod 0644 "$RESOLV_DST"

echo '[AI] Verifying network/DNS inside Fedora chroot'
sudo chroot "$ROOT_TREE" /usr/bin/getent hosts mirrors.fedoraproject.org >/dev/null

echo '[AI] Installing local inference, containment and audio runtime'
sudo chroot "$ROOT_TREE" /usr/bin/dnf -y --setopt=retries=5 --setopt=timeout=30 install \
  ollama whisper-cpp espeak-ng alsa-utils pipewire-utils libsndfile python3-psutil python3-pip bubblewrap
sudo chroot "$ROOT_TREE" /usr/bin/dnf clean all

# IMPORTANT: the immutable Live image must not pip-install the PyTorch Kokoro or
# Chatterbox stacks. On Linux pip can resolve multi-gigabyte CUDA wheels even on a
# CPU build runner. Run #17 exhausted the GitHub filesystem this way. Quantic uses
# Kokoro-82M through ONNX Runtime in the base image: same ff_siwis French voice,
# no Torch/CUDA dependency. Chatterbox remains an optional post-boot quality tier.
echo '[AI] Installing compact Kokoro ONNX neural voice runtime'
sudo chroot "$ROOT_TREE" /usr/bin/env PIP_DISABLE_PIP_VERSION_CHECK=1 \
  /usr/bin/python3 -m pip install --no-cache-dir --break-system-packages --retries 3 --timeout 60 \
  'kokoro-onnx==0.6.1' soundfile 'misaki-fork[en]' || \
  echo '[AI] WARNING: Kokoro ONNX unavailable; Piper fallback will remain usable.'

# Piper is deliberately independent of the premium engine so the OS always has a
# small offline voice even if optional Python wheels are unavailable.
sudo chroot "$ROOT_TREE" /usr/bin/env PIP_DISABLE_PIP_VERSION_CHECK=1 \
  /usr/bin/python3 -m pip install --no-cache-dir --break-system-packages --retries 3 --timeout 60 piper-tts || \
  echo '[AI] WARNING: Piper install unavailable; espeak-ng remains last-resort audio tooling.'
sudo rm -rf "$ROOT_TREE/root/.cache/pip" "$ROOT_TREE/tmp/pip-"* 2>/dev/null || true

echo '[AI] Embedding Kokoro-82M ONNX model and French-capable voice bank'
KOKORO_RELEASE='https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0'
sudo curl -fL --retry 5 --retry-all-errors "$KOKORO_RELEASE/kokoro-v1.0.onnx" -o "$KOKORO_DIR/kokoro-v1.0.onnx"
sudo curl -fL --retry 5 --retry-all-errors "$KOKORO_RELEASE/voices-v1.0.bin" -o "$KOKORO_DIR/voices-v1.0.bin"
test -s "$KOKORO_DIR/kokoro-v1.0.onnx"
test -s "$KOKORO_DIR/voices-v1.0.bin"

echo '[AI] Embedding compact speech-recognition model'
WHISPER_URL='https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin?download=true'
sudo curl -fL --retry 5 --retry-all-errors "$WHISPER_URL" -o "$MODEL_DIR/ggml-base.bin"
test -s "$MODEL_DIR/ggml-base.bin"

echo '[AI] Embedding French Piper fallback voice'
PIPER_BASE='https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium'
sudo curl -fL --retry 5 --retry-all-errors "$PIPER_BASE/fr_FR-siwis-medium.onnx?download=true" -o "$MODEL_DIR/fr_FR-siwis-medium.onnx"
sudo curl -fL --retry 5 --retry-all-errors "$PIPER_BASE/fr_FR-siwis-medium.onnx.json?download=true" -o "$MODEL_DIR/fr_FR-siwis-medium.onnx.json"
test -s "$MODEL_DIR/fr_FR-siwis-medium.onnx"
test -s "$MODEL_DIR/fr_FR-siwis-medium.onnx.json"

echo '[AI] Warming low-latency French neural voice'
if [[ -f "$ROOT_TREE/usr/lib/quantic/services/qvoice_neural.py" ]]; then
  sudo chroot "$ROOT_TREE" /usr/bin/env HF_HUB_DISABLE_TELEMETRY=1 \
    /usr/bin/python3 /usr/lib/quantic/services/qvoice_neural.py \
    --engine kokoro --warmup --output /tmp/quantic-voice-warmup.wav >/tmp/quantic-voice-warmup.json 2>/tmp/quantic-voice-warmup.err || \
    echo '[AI] WARNING: neural warmup failed; runtime will fall back safely.'
  sudo rm -f "$ROOT_TREE/tmp/quantic-voice-warmup.wav" "$ROOT_TREE/tmp/quantic-voice-warmup.json" "$ROOT_TREE/tmp/quantic-voice-warmup.err" || true
else
  echo '[AI] WARNING: qvoice_neural.py absent; skipping neural warmup.'
fi

sudo chmod -R a+rX "$ROOT_TREE/usr/share/quantic"

echo '[AI] Verifying runtime payload'
test -x "$ROOT_TREE/usr/bin/ollama"
test -x "$ROOT_TREE/usr/bin/bwrap"
test -s "$KOKORO_DIR/kokoro-v1.0.onnx"
test -s "$KOKORO_DIR/voices-v1.0.bin"
test -s "$MODEL_DIR/ggml-base.bin"
test -s "$MODEL_DIR/fr_FR-siwis-medium.onnx"

echo '[AI] Runtime ready. Voice policy: Kokoro-82M ONNX French by default, Piper fallback; Chatterbox optional after boot.'
exit 0
