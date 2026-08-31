#!/usr/bin/env bash
set -euo pipefail

ROOT_TREE=${1:?Usage: provision-final-ai.sh ROOT_TREE WORKDIR}
WORK=${2:?Usage: provision-final-ai.sh ROOT_TREE WORKDIR}
MODEL_DIR="$ROOT_TREE/usr/share/quantic/models"
OLLAMA_DST="$ROOT_TREE/usr/share/quantic/ollama-models"
OLLAMA_CACHE="$WORK/ollama-models"
RESOLV_DST="$ROOT_TREE/etc/resolv.conf"
RESOLV_BACKUP="$WORK/resolv.conf.root-tree.backup"
HAD_RESOLV=0

sudo mkdir -p "$MODEL_DIR" "$OLLAMA_DST" "$OLLAMA_CACHE" "$WORK"

restore_resolver() {
  if [[ "$HAD_RESOLV" == 1 && -f "$RESOLV_BACKUP" ]]; then
    sudo cp -L "$RESOLV_BACKUP" "$RESOLV_DST"
  else
    sudo rm -f "$RESOLV_DST"
  fi
}
trap restore_resolver EXIT

# The extracted Fedora Live root can contain a resolv.conf symlink that only
# becomes valid after boot. During CI chroot provisioning that leaves dnf/pip
# without DNS even though the GitHub runner itself has working networking.
# Seed the chroot with the runner resolver, then restore the Live image state.
if [[ -e "$RESOLV_DST" || -L "$RESOLV_DST" ]]; then
  sudo cp -L "$RESOLV_DST" "$RESOLV_BACKUP" 2>/dev/null || true
  HAD_RESOLV=1
fi
sudo rm -f "$RESOLV_DST"
sudo cp -L /etc/resolv.conf "$RESOLV_DST"
sudo chmod 0644 "$RESOLV_DST"

echo '[AI] Verifying network/DNS inside Fedora chroot'
sudo chroot "$ROOT_TREE" /usr/bin/getent hosts mirrors.fedoraproject.org >/dev/null

echo '[AI] Installing Fedora-native local inference/audio runtime'
sudo chroot "$ROOT_TREE" /usr/bin/dnf -y --setopt=retries=5 --setopt=timeout=30 install \
  ollama whisper-cpp espeak-ng alsa-utils pipewire-utils python3-psutil python3-pip
sudo chroot "$ROOT_TREE" /usr/bin/dnf clean all

# Piper gives a substantially more natural local voice than espeak-ng. Keep
# espeak-ng as a guaranteed fallback if Python wheels ever stop resolving.
echo '[AI] Installing local Piper neural TTS runtime'
sudo chroot "$ROOT_TREE" /usr/bin/python3 -m pip install --no-cache-dir --break-system-packages piper-tts || \
  echo '[AI] WARNING: Piper install unavailable; espeak-ng fallback remains installed.'

echo '[AI] Embedding multilingual local speech-recognition model'
WHISPER_URL='https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin?download=true'
sudo curl -fL --retry 5 --retry-all-errors "$WHISPER_URL" -o "$MODEL_DIR/ggml-base.bin"
test -s "$MODEL_DIR/ggml-base.bin"

echo '[AI] Embedding French neural voice'
PIPER_BASE='https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium'
sudo curl -fL --retry 5 --retry-all-errors "$PIPER_BASE/fr_FR-siwis-medium.onnx?download=true" -o "$MODEL_DIR/fr_FR-siwis-medium.onnx"
sudo curl -fL --retry 5 --retry-all-errors "$PIPER_BASE/fr_FR-siwis-medium.onnx.json?download=true" -o "$MODEL_DIR/fr_FR-siwis-medium.onnx.json"
test -s "$MODEL_DIR/fr_FR-siwis-medium.onnx"
test -s "$MODEL_DIR/fr_FR-siwis-medium.onnx.json"

echo '[AI] Preloading Quantic default LLM so first boot works without API keys'
rm -rf "$OLLAMA_CACHE" && mkdir -p "$OLLAMA_CACHE"
docker run --rm -v "$OLLAMA_CACHE:/models" fedora:44 bash -lc '
  set -euo pipefail
  dnf -y --setopt=retries=5 --setopt=timeout=30 install ollama >/dev/null
  export OLLAMA_MODELS=/models
  export OLLAMA_HOST=127.0.0.1:11434
  ollama serve >/tmp/ollama.log 2>&1 &
  pid=$!
  trap "kill $pid 2>/dev/null || true" EXIT
  ok=0
  for i in $(seq 1 60); do
    if ollama list >/dev/null 2>&1; then ok=1; break; fi
    sleep 1
  done
  [[ "$ok" == 1 ]] || { cat /tmp/ollama.log; exit 2; }
  ollama pull qwen3:4b
  ollama list
'
sudo rsync -a "$OLLAMA_CACHE/" "$OLLAMA_DST/"
sudo chmod -R a+rX "$ROOT_TREE/usr/share/quantic"

echo '[AI] Verifying embedded voice/brain payload'
test -x "$ROOT_TREE/usr/bin/ollama"
command -v docker >/dev/null
test -s "$OLLAMA_DST/manifests/registry.ollama.ai/library/qwen3/4b" || {
  echo 'Embedded qwen3:4b manifest not found' >&2
  find "$OLLAMA_DST" -maxdepth 6 -type f | head -50 >&2
  exit 3
}

echo '[AI] Offline local AI payload ready: Ollama + qwen3:4b + whisper.cpp + Piper voice'
