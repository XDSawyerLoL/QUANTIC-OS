#!/usr/bin/env bash
set -Eeuo pipefail
trap 'rc=$?; echo "[ERROR] remaster failed at line ${BASH_LINENO[0]}: ${BASH_COMMAND} (exit ${rc})" >&2; exit ${rc}' ERR

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
WORK="${QUANTIC_WORKDIR:-$ROOT/build/final-remaster}"
OUT_DIR="$ROOT/build/live"
BASE_ISO="$WORK/Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso"
BASE_URL="${FEDORA_BASE_URL:-https://download.fedoraproject.org/pub/fedora/linux/releases/44/KDE/x86_64/iso/Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso}"
BASE_SHA256="c8295961d4c41adbf785a31a17c21a971d3b7415fda72dcad0c11c49577bf03a"
OUT_ISO="$OUT_DIR/Quantic-OS-Final-Live-x86_64.iso"
EROFS_ORIG="$WORK/liveos-original.erofs"
EROFS_NEW="$WORK/liveos-quantic.erofs"
ROOT_TREE="$WORK/root-tree"
SRC_MNT="$WORK/source-mnt"
VERIFY_MNT="$WORK/verify-mnt"
VERIFY_IMG="$WORK/verify-liveos.erofs"
QBUILD="$WORK/qbuild"
SRC_MOUNTED=0
VERIFY_MOUNTED=0

cleanup() {
  [[ "$VERIFY_MOUNTED" == 1 ]] && sudo umount "$VERIFY_MNT" || true
  [[ "$SRC_MOUNTED" == 1 ]] && sudo umount "$SRC_MNT" || true
}
trap cleanup EXIT
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 2; }; }
for cmd in curl sha256sum xorriso mount umount docker rsync blkid mkfs.erofs fsck.erofs; do need "$cmd"; done
mkdir -p "$WORK" "$OUT_DIR" "$SRC_MNT" "$VERIFY_MNT"

echo '[1/10] Building Quantic Home against Fedora 44 Qt 6'
rm -rf "$QBUILD" && mkdir -p "$QBUILD"
docker run --rm -v "$ROOT:/src:ro" -v "$QBUILD:/build" fedora:44 bash -lc '
  set -euxo pipefail
  dnf -y install gcc-c++ cmake ninja-build qt6-qtbase-devel qt6-qtdeclarative-devel qt6-qtsvg-devel
  cmake -S /src/shell -B /build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
  cmake --build /build --parallel "$(nproc)"
  test -x /build/quantic-home
'

echo '[2/10] Downloading and verifying official Fedora KDE 44 Live ISO'
if [[ ! -f "$BASE_ISO" ]]; then curl -fL --retry 5 --retry-all-errors --continue-at - "$BASE_URL" -o "$BASE_ISO"; fi
echo "$BASE_SHA256  $BASE_ISO" | sha256sum -c -

echo '[3/10] Extracting Fedora LiveOS EROFS payload'
rm -f "$EROFS_ORIG" "$EROFS_NEW" "$VERIFY_IMG" && rm -rf "$ROOT_TREE"
xorriso -osirrox on -indev "$BASE_ISO" -extract /LiveOS/squashfs.img "$EROFS_ORIG" >/dev/null 2>&1
[[ "$(blkid -o value -s TYPE "$EROFS_ORIG" || true)" == "erofs" ]] || { echo 'Fedora LiveOS is not EROFS' >&2; exit 3; }
fsck.erofs "$EROFS_ORIG" >/dev/null

echo '[4/10] Copying root tree'
sudo mount -t erofs -o loop,ro "$EROFS_ORIG" "$SRC_MNT"; SRC_MOUNTED=1
sudo mkdir -p "$ROOT_TREE"
sudo rsync -aHAX --numeric-ids "$SRC_MNT/" "$ROOT_TREE/"
sudo umount "$SRC_MNT"; SRC_MOUNTED=0

echo '[5/10] Injecting Quantic runtime + agent platform'
sudo install -D -m 0755 "$QBUILD/quantic-home" "$ROOT_TREE/usr/libexec/quantic-home"
sudo install -D -m 0644 "$ROOT/shell/autostart/quantic-home.desktop" "$ROOT_TREE/etc/xdg/autostart/quantic-home.desktop"
sudo mkdir -p "$ROOT_TREE/usr/lib/quantic/services" "$ROOT_TREE/etc/quantic" "$ROOT_TREE/usr/share/backgrounds/quantic"
sudo rsync -a "$ROOT/services/" "$ROOT_TREE/usr/lib/quantic/services/"
sudo rsync -a "$ROOT/config/" "$ROOT_TREE/etc/quantic/"
sudo find "$ROOT_TREE/usr/lib/quantic/services" -type f \( -name '*.py' -o -name '*.sh' \) -exec chmod 0755 {} +
sudo install -m 0644 "$ROOT/assets/quantic-wallpaper.svg" "$ROOT_TREE/usr/share/backgrounds/quantic/quantic-wallpaper.svg"
if [[ -d "$ROOT/plasma/org.quantic.desktop" ]]; then
  sudo mkdir -p "$ROOT_TREE/usr/share/plasma/look-and-feel/org.quantic.desktop"
  sudo rsync -a "$ROOT/plasma/org.quantic.desktop/" "$ROOT_TREE/usr/share/plasma/look-and-feel/org.quantic.desktop/"
fi

echo '[6/10] Provisioning compact local AI runtime, ears, voice and containment'
chmod +x "$ROOT/scripts/provision-final-ai.sh"
"$ROOT/scripts/provision-final-ai.sh" "$ROOT_TREE" "$WORK"

echo '[6b/10] Installing and enabling Quantic V2 services'
for unit in quantic-usb-safe.service quantic-persistence.service quantic-health.service quantic-core.target quantic-ollama.service quantic-dream.service quantic-dream.timer; do
  echo "[SERVICES] Installing $unit"
  sudo install -D -m 0644 "$ROOT/systemd/$unit" "$ROOT_TREE/usr/lib/systemd/system/$unit"
done
sudo mkdir -p "$ROOT_TREE/etc/systemd/system/local-fs.target.wants" "$ROOT_TREE/etc/systemd/system/multi-user.target.wants" "$ROOT_TREE/etc/systemd/system/timers.target.wants"
sudo ln -sfn /usr/lib/systemd/system/quantic-usb-safe.service "$ROOT_TREE/etc/systemd/system/local-fs.target.wants/quantic-usb-safe.service"
sudo ln -sfn /usr/lib/systemd/system/quantic-persistence.service "$ROOT_TREE/etc/systemd/system/local-fs.target.wants/quantic-persistence.service"
sudo ln -sfn /usr/lib/systemd/system/quantic-core.target "$ROOT_TREE/etc/systemd/system/multi-user.target.wants/quantic-core.target"
sudo ln -sfn /usr/lib/systemd/system/quantic-ollama.service "$ROOT_TREE/etc/systemd/system/multi-user.target.wants/quantic-ollama.service"
sudo ln -sfn /usr/lib/systemd/system/quantic-dream.timer "$ROOT_TREE/etc/systemd/system/timers.target.wants/quantic-dream.timer"

# The modern desktop CompanionBridge owns push-to-talk, adaptive VAD, streaming
# LLM-to-TTS and interruption. Keep the legacy wake daemon installed only as an
# opt-in compatibility unit; never start a permanent microphone listener by default.
for unit in quantic-companion.service quantic-voice.service; do
  echo "[SERVICES] Installing user/$unit"
  sudo install -D -m 0644 "$ROOT/systemd/user/$unit" "$ROOT_TREE/usr/lib/systemd/user/$unit"
done
sudo mkdir -p "$ROOT_TREE/etc/systemd/user/default.target.wants"
sudo ln -sfn /usr/lib/systemd/user/quantic-companion.service "$ROOT_TREE/etc/systemd/user/default.target.wants/quantic-companion.service"
sudo rm -f "$ROOT_TREE/etc/systemd/user/default.target.wants/quantic-voice.service"

sudo mkdir -p "$ROOT_TREE/usr/local/share/applications"
for desktop_id in liveinst.desktop org.fedoraproject.AnacondaInstaller.desktop org.fedoraproject.Anaconda.desktop; do
  sudo tee "$ROOT_TREE/usr/local/share/applications/$desktop_id" >/dev/null <<EOF
[Desktop Entry]
Type=Application
Name=Installer disabled in Quantic Live
Hidden=true
NoDisplay=true
EOF
done

sudo tee "$ROOT_TREE/etc/quantic-release" >/dev/null <<'EOF'
NAME="Quantic OS"
VERSION="V2 Final Live Split-AI"
BASE="Fedora KDE Plasma Desktop 44"
BUILD_STRATEGY="verified-fedora-erofs-remaster"
RUNTIME="quantic-v2+agent-runtime+memory+dream+companion+kokoro-onnx+ollama+whisper+piper+persistence+health+containment"
LOCAL_MODEL="external:QUANTIC-DATA/models/ollama"
VOICE_MODE="push-to-talk-adaptive-local"
LEGACY_WAKE_DAEMON="installed-disabled"
PERSISTENCE="usb-only:QUANTIC-DATA"
EOF

sudo chroot "$ROOT_TREE" /sbin/restorecon -RF /usr/libexec/quantic-home /etc/xdg/autostart/quantic-home.desktop /usr/lib/quantic /etc/quantic /usr/lib/systemd/system/quantic-* /usr/lib/systemd/user/quantic-* /usr/share/quantic /usr/share/backgrounds/quantic /usr/share/plasma/look-and-feel/org.quantic.desktop /usr/local/share/applications 2>/dev/null || true

echo '[6c/10] Validating injected V2 runtime'
for f in qagent.py qagent_runtime.py qpolicy.py qsimulation.py qcontainment.py qtoolrouter.py qtwin.py qverify.py qrollback.py qskills.py qmcp.py qtasks.py qpersistence.py qhealth.py qvoice.py qvoice_neural.py qdream.py qdream_runner.py; do
  sudo test -x "$ROOT_TREE/usr/lib/quantic/services/$f"
done
sudo test -x "$ROOT_TREE/usr/libexec/quantic-home"
sudo test -x "$ROOT_TREE/usr/bin/ollama"
sudo test -x "$ROOT_TREE/usr/bin/bwrap"
sudo test -s "$ROOT_TREE/usr/share/quantic/models/kokoro/kokoro-v1.0.onnx"
sudo test -s "$ROOT_TREE/usr/share/quantic/models/kokoro/voices-v1.0.bin"
sudo test -s "$ROOT_TREE/usr/share/quantic/models/ggml-base.bin"
sudo test -s "$ROOT_TREE/usr/share/quantic/models/fr_FR-siwis-medium.onnx"
sudo test -L "$ROOT_TREE/etc/systemd/system/local-fs.target.wants/quantic-usb-safe.service"
sudo test -L "$ROOT_TREE/etc/systemd/system/multi-user.target.wants/quantic-core.target"
sudo test -L "$ROOT_TREE/etc/systemd/system/multi-user.target.wants/quantic-ollama.service"
sudo test -L "$ROOT_TREE/etc/systemd/system/timers.target.wants/quantic-dream.timer"
! sudo test -L "$ROOT_TREE/etc/systemd/user/default.target.wants/quantic-voice.service"
sudo grep -q 'OLLAMA_MODELS=/var/lib/quantic/models/ollama' "$ROOT_TREE/usr/lib/systemd/system/quantic-ollama.service"
sudo grep -q 'VOICE_MODE="push-to-talk-adaptive-local"' "$ROOT_TREE/etc/quantic-release"

echo '[7/10] Repacking LiveOS as fast EROFS LZ4HC'
sudo mkfs.erofs -zlz4hc -Eall-fragments -C1048576 "$EROFS_NEW" "$ROOT_TREE"
fsck.erofs "$EROFS_NEW" >/dev/null

echo '[8/10] Replaying Fedora boot metadata'
rm -f "$OUT_ISO"
xorriso -indev "$BASE_ISO" -outdev "$OUT_ISO" -boot_image any replay -map "$EROFS_NEW" /LiveOS/squashfs.img -commit >/dev/null 2>&1

echo '[9/10] Structural, runtime, V2 and boot validation'
test -s "$OUT_ISO"
xorriso -indev "$OUT_ISO" -report_el_torito plain > "$WORK/el-torito.txt" 2>&1
grep -Eqi 'UEFI|EFI|El Torito' "$WORK/el-torito.txt"
xorriso -osirrox on -indev "$OUT_ISO" -extract /LiveOS/squashfs.img "$VERIFY_IMG" >/dev/null 2>&1
[[ "$(blkid -o value -s TYPE "$VERIFY_IMG" || true)" == "erofs" ]]
fsck.erofs "$VERIFY_IMG" >/dev/null
sudo mount -t erofs -o loop,ro "$VERIFY_IMG" "$VERIFY_MNT"; VERIFY_MOUNTED=1
sudo test -x "$VERIFY_MNT/usr/libexec/quantic-home"
sudo test -x "$VERIFY_MNT/usr/lib/quantic/services/qagent_runtime.py"
sudo test -x "$VERIFY_MNT/usr/lib/quantic/services/qpolicy.py"
sudo test -x "$VERIFY_MNT/usr/lib/quantic/services/qsimulation.py"
sudo test -x "$VERIFY_MNT/usr/lib/quantic/services/qcontainment.py"
sudo test -x "$VERIFY_MNT/usr/lib/quantic/services/qvoice_neural.py"
sudo test -x "$VERIFY_MNT/usr/bin/ollama"
sudo test -x "$VERIFY_MNT/usr/bin/bwrap"
sudo test -s "$VERIFY_MNT/usr/share/quantic/models/kokoro/kokoro-v1.0.onnx"
sudo test -s "$VERIFY_MNT/usr/share/quantic/models/kokoro/voices-v1.0.bin"
sudo test -s "$VERIFY_MNT/usr/share/quantic/models/ggml-base.bin"
sudo test -L "$VERIFY_MNT/etc/systemd/system/multi-user.target.wants/quantic-core.target"
sudo test -L "$VERIFY_MNT/etc/systemd/system/multi-user.target.wants/quantic-ollama.service"
sudo test -L "$VERIFY_MNT/etc/systemd/system/timers.target.wants/quantic-dream.timer"
! sudo test -L "$VERIFY_MNT/etc/systemd/user/default.target.wants/quantic-voice.service"
sudo grep -q 'LOCAL_MODEL="external:QUANTIC-DATA/models/ollama"' "$VERIFY_MNT/etc/quantic-release"
sudo grep -q 'VOICE_MODE="push-to-talk-adaptive-local"' "$VERIFY_MNT/etc/quantic-release"
! sudo test -d "$VERIFY_MNT/usr/share/quantic/ollama-models"
sudo umount "$VERIFY_MNT"; VERIFY_MOUNTED=0
sha256sum "$OUT_ISO" > "$OUT_ISO.sha256"

echo '[10/10] Quantic OS V2 split-runtime image complete'
ls -lh "$OUT_ISO" "$OUT_ISO.sha256"
echo "Built: $OUT_ISO"
echo 'Quantic V2 runtime, compact neural voice and containment are embedded. Large LLM weights persist on removable QUANTIC-DATA.'
echo 'NOTE: CI validation is not physical hardware certification.'
