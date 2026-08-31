#!/usr/bin/env bash
set -euo pipefail

ROOT_TREE=${1:?Usage: provision-final-ai.sh ROOT_TREE WORKDIR}
WORK=${2:?Usage: provision-final-ai.sh ROOT_TREE WORKDIR}
MODEL_DIR="$ROOT_TREE/usr/share/quantic/models"
RESOLV_DST="$ROOT_TREE/etc/resolv.conf"
RESOLV_BACKUP="$WORK/resolv.conf.root-tree.backup"
HAD_RESOLV=0

sudo mkdir -p "$MODEL_DIR" "$WORK"

restore_resolver() {
  if [[ "$HAD_RESOLV" == 1 && -f "$RESOLV_BACKUP" ]]; then
    sudo cp -L "$RESOLV_BACKUP" "$RESOLV_DST"
  else
    sudo rm -f "$RESOLV_DST"
  fi
}
trap restore_resolver EXIT

if [[ -e "$RESOLV_DST" || -L "$RESOLV_DST" ]]; then
  sudo cp -L "$RESOLV_DST" "$RESOLV_BACKUP" 2>/dev/null || true
  HAD_RESOLV=1
fi
sudo rm -f "$RESOLV_DST"
sudo cp -L /etc/resolv.conf "$RESOLV_DST"
sudo chmod 0644 "$RESOLV_DST"

echo '[AI] Verifying network/DNS inside Fedora chroot'
sudo chroot "$ROOT_TREE" /usr/bin/getent hosts mirrors.fedoraproject.org >/dev/null

echo '[AI] Installing local inference, containment and audio runtime'
sudo chroot "$ROOT_TREE" /usr/bin/dnf -y --setopt=retries=5 --setopt=timeout=30 install \
  ollama whisper-cpp espeak-ng alsa-utils pipewire-utils python3-psutil python3-pip bubblewrap
sudo chroot "$ROOT_TREE" /usr/bin/dnf clean all

echo '[AI] Installing local Piper neural TTS runtime'
sudo chroot "$ROOT_TREE" /usr/bin/python3 -m pip install --no-cache-dir --break-system-packages piper-tts || \
  echo '[AI] WARNING: Piper install unavailable; espeak-ng fallback remains installed.'

echo '[AI] Embedding compact speech-recognition model'
WHISPER_URL='https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin?download=true'
sudo curl -fL --retry 5 --retry-all-errors "$WHISPER_URL" -o "$MODEL_DIR/ggml-base.bin"
test -s "$MODEL_DIR/ggml-base.bin"

echo '[AI] Embedding French neural voice'
PIPER_BASE='https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium'
sudo curl -fL --retry 5 --retry-all-errors "$PIPER_BASE/fr_FR-siwis-medium.onnx?download=true" -o "$MODEL_DIR/fr_FR-siwis-medium.onnx"
sudo curl -fL --retry 5 --retry-all-errors "$PIPER_BASE/fr_FR-siwis-medium.onnx.json?download=true" -o "$MODEL_DIR/fr_FR-siwis-medium.onnx.json"
test -s "$MODEL_DIR/fr_FR-siwis-medium.onnx"
test -s "$MODEL_DIR/fr_FR-siwis-medium.onnx.json"
sudo chmod -R a+rX "$ROOT_TREE/usr/share/quantic"

echo '[AI] Verifying runtime payload'
test -x "$ROOT_TREE/usr/bin/ollama"
test -x "$ROOT_TREE/usr/bin/bwrap"
test -s "$MODEL_DIR/ggml-base.bin"
test -s "$MODEL_DIR/fr_FR-siwis-medium.onnx"

echo '[AI] Runtime ready. Large LLM weights are intentionally stored on QUANTIC-DATA, not in the ISO.'
