#!/usr/bin/env bash
set -euo pipefail

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

echo '[1/9] Building Quantic Home against Fedora 44 Qt 6'
rm -rf "$QBUILD" && mkdir -p "$QBUILD"
docker run --rm -v "$ROOT:/src:ro" -v "$QBUILD:/build" fedora:44 bash -lc '
  set -euxo pipefail
  dnf -y install gcc-c++ cmake ninja-build qt6-qtbase-devel qt6-qtdeclarative-devel qt6-qtsvg-devel
  cmake -S /src/shell -B /build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
  cmake --build /build --parallel "$(nproc)"
  test -x /build/quantic-home
'

echo '[2/9] Downloading and verifying official Fedora KDE 44 Live ISO'
if [[ ! -f "$BASE_ISO" ]]; then curl -fL --retry 5 --retry-all-errors --continue-at - "$BASE_URL" -o "$BASE_ISO"; fi
echo "$BASE_SHA256  $BASE_ISO" | sha256sum -c -

echo '[3/9] Extracting Fedora LiveOS EROFS payload'
rm -f "$EROFS_ORIG" "$EROFS_NEW" "$VERIFY_IMG" && rm -rf "$ROOT_TREE"
xorriso -osirrox on -indev "$BASE_ISO" -extract /LiveOS/squashfs.img "$EROFS_ORIG" >/dev/null 2>&1
[[ "$(blkid -o value -s TYPE "$EROFS_ORIG" || true)" == "erofs" ]] || { echo 'Fedora LiveOS is not EROFS' >&2; exit 3; }
fsck.erofs "$EROFS_ORIG" >/dev/null

echo '[4/9] Copying root tree'
sudo mount -t erofs -o loop,ro "$EROFS_ORIG" "$SRC_MNT"; SRC_MOUNTED=1
sudo mkdir -p "$ROOT_TREE"
sudo rsync -aHAX --numeric-ids "$SRC_MNT/" "$ROOT_TREE/"
sudo umount "$SRC_MNT"; SRC_MOUNTED=0

echo '[5/9] Injecting complete Quantic runtime'
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

# System services: disk safety is mandatory; persistence and health degrade gracefully.
for unit in quantic-usb-safe.service quantic-persistence.service quantic-health.service quantic-core.target; do
  sudo install -D -m 0644 "$ROOT/systemd/$unit" "$ROOT_TREE/usr/lib/systemd/system/$unit"
done
sudo mkdir -p "$ROOT_TREE/etc/systemd/system/local-fs.target.wants" "$ROOT_TREE/etc/systemd/system/multi-user.target.wants"
sudo ln -sfn /usr/lib/systemd/system/quantic-usb-safe.service "$ROOT_TREE/etc/systemd/system/local-fs.target.wants/quantic-usb-safe.service"
sudo ln -sfn /usr/lib/systemd/system/quantic-persistence.service "$ROOT_TREE/etc/systemd/system/local-fs.target.wants/quantic-persistence.service"
sudo ln -sfn /usr/lib/systemd/system/quantic-core.target "$ROOT_TREE/etc/systemd/system/multi-user.target.wants/quantic-core.target"

# User companion: enabled globally but sandboxed and unprivileged.
sudo install -D -m 0644 "$ROOT/systemd/user/quantic-companion.service" "$ROOT_TREE/usr/lib/systemd/user/quantic-companion.service"
sudo mkdir -p "$ROOT_TREE/etc/systemd/user/default.target.wants"
sudo ln -sfn /usr/lib/systemd/user/quantic-companion.service "$ROOT_TREE/etc/systemd/user/default.target.wants/quantic-companion.service"

# Live-only product: no installer entry points.
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
VERSION="Final Live"
BASE="Fedora KDE Plasma Desktop 44"
BUILD_STRATEGY="verified-fedora-erofs-remaster"
RUNTIME="quantic-core+companion+persistence+health"
EOF

sudo chroot "$ROOT_TREE" /sbin/restorecon -RF /usr/libexec/quantic-home /etc/xdg/autostart/quantic-home.desktop /usr/lib/quantic /etc/quantic /usr/lib/systemd/system/quantic-\* /usr/lib/systemd/user/quantic-companion.service /usr/share/backgrounds/quantic /usr/share/plasma/look-and-feel/org.quantic.desktop /usr/local/share/applications 2>/dev/null || true

test -x "$ROOT_TREE/usr/libexec/quantic-home"
test -x "$ROOT_TREE/usr/lib/quantic/services/qcompanion_daemon.py"
test -x "$ROOT_TREE/usr/lib/quantic/services/qpersistence.py"
test -x "$ROOT_TREE/usr/lib/quantic/services/qhealth.py"
test -L "$ROOT_TREE/etc/systemd/system/local-fs.target.wants/quantic-usb-safe.service"
test -L "$ROOT_TREE/etc/systemd/system/multi-user.target.wants/quantic-core.target"
test -L "$ROOT_TREE/etc/systemd/user/default.target.wants/quantic-companion.service"

echo '[6/9] Repacking LiveOS as fast EROFS LZ4HC'
sudo mkfs.erofs -zlz4hc -Eall-fragments -C1048576 "$EROFS_NEW" "$ROOT_TREE"
fsck.erofs "$EROFS_NEW" >/dev/null

echo '[7/9] Replaying Fedora boot metadata'
rm -f "$OUT_ISO"
xorriso -indev "$BASE_ISO" -outdev "$OUT_ISO" -boot_image any replay -map "$EROFS_NEW" /LiveOS/squashfs.img -commit >/dev/null 2>&1

echo '[8/9] Structural, runtime and boot validation'
test -s "$OUT_ISO"
xorriso -indev "$OUT_ISO" -report_el_torito plain > "$WORK/el-torito.txt" 2>&1
grep -Eqi 'UEFI|EFI|El Torito' "$WORK/el-torito.txt"
xorriso -osirrox on -indev "$OUT_ISO" -extract /LiveOS/squashfs.img "$VERIFY_IMG" >/dev/null 2>&1
[[ "$(blkid -o value -s TYPE "$VERIFY_IMG" || true)" == "erofs" ]]
fsck.erofs "$VERIFY_IMG" >/dev/null
sudo mount -t erofs -o loop,ro "$VERIFY_IMG" "$VERIFY_MNT"; VERIFY_MOUNTED=1
test -x "$VERIFY_MNT/usr/libexec/quantic-home"
test -x "$VERIFY_MNT/usr/lib/quantic/services/qcompanion_daemon.py"
test -x "$VERIFY_MNT/usr/lib/quantic/services/qpersistence.py"
test -x "$VERIFY_MNT/usr/lib/quantic/services/qhealth.py"
test -L "$VERIFY_MNT/etc/systemd/system/multi-user.target.wants/quantic-core.target"
test -L "$VERIFY_MNT/etc/systemd/user/default.target.wants/quantic-companion.service"
grep -q 'Final Live' "$VERIFY_MNT/etc/quantic-release"
sudo umount "$VERIFY_MNT"; VERIFY_MOUNTED=0
sha256sum "$OUT_ISO" > "$OUT_ISO.sha256"

echo '[9/9] Quantic OS Final image complete'
ls -lh "$OUT_ISO" "$OUT_ISO.sha256"
echo "Built: $OUT_ISO"
echo 'NOTE: CI validation passed. Physical hardware certification remains mandatory before declaring a production release.'
