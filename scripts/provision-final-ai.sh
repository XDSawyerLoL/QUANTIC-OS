#!/usr/bin/env bash
set -euo pipefail

ROOT_TREE=${1:?Usage: provision-final-ai.sh ROOT_TREE WORKDIR}
WORK=${2:?Usage: provision-final-ai.sh ROOT_TREE WORKDIR}
MODEL_DIR="$ROOT_TREE/usr/share/quantic/models"
HF_DIR="$MODEL_DIR/hf"
RESOLV_DST="$ROOT_TREE/etc/resolv.conf"
RESOLV_BACKUP="$WORK/resolv.conf.root-tree.backup"
HAD_RESOLV=0

sudo mkdir -p "$MODEL_DIR" "$HF_DIR" "$WORK"

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

echo '[AI] Installing compact premium neural voice stack'
# Kokoro is deliberately embedded as the always-available neural conversation path.
# Chatterbox remains supported by qvoice_neural.py, but is NOT installed in the
# immutable Live image: its PyPI dependency graph can resolve several gigabytes of
# CUDA/Torch wheels, which bloats the ISO and can exhaust the remaster job budget.
# On capable NVIDIA hardware it can be supplied later as an optional accelerator;
# absence is intentional and qvoice_neural.py deterministically falls back to Kokoro.
sudo chroot "$ROOT_TREE" /usr/bin/env PIP_DISABLE_PIP_VERSION_CHECK=1 \
  /usr/bin/python3 -m pip install --no-cache-dir --break-system-packages --retries 3 --timeout 60 \
  'kokoro>=0.9.4' soundfile numpy || \
  echo '[AI] WARNING: Kokoro unavailable; Piper fallback will remain usable.'
sudo chroot "$ROOT_TREE" /usr/bin/env PIP_DISABLE_PIP_VERSION_CHECK=1 \
  /usr/bin/python3 -m pip install --no-cache-dir --break-system-packages --retries 3 --timeout 60 piper-tts || \
  echo '[AI] WARNING: Piper install unavailable; espeak-ng remains last-resort audio tooling.'
sudo rm -rf "$ROOT_TREE/root/.cache/pip" "$ROOT_TREE/tmp/pip-"* 2>/dev/null || true

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

echo '[AI] Warming low-latency French neural cache'
if [[ -f "$ROOT_TREE/usr/lib/quantic/services/qvoice_neural.py" ]]; then
  sudo chroot "$ROOT_TREE" /usr/bin/env HF_HOME=/usr/share/quantic/models/hf HF_HUB_DISABLE_TELEMETRY=1 \
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
test -s "$MODEL_DIR/ggml-base.bin"
test -s "$MODEL_DIR/fr_FR-siwis-medium.onnx"

echo '[AI] Runtime ready. Voice policy: Kokoro neural low-latency by default, Piper fallback; Chatterbox is an optional post-boot quality accelerator.'
exit 0
