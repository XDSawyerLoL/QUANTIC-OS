#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
WORK="${QUANTIC_WORKDIR:-$ROOT/build/remaster}"
OUT_DIR="$ROOT/build/live"
BASE_ISO="$WORK/Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso"
BASE_URL="${FEDORA_BASE_URL:-https://download.fedoraproject.org/pub/fedora/linux/releases/44/KDE/x86_64/iso/Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso}"
BASE_SHA256="c8295961d4c41adbf785a31a17c21a971d3b7415fda72dcad0c11c49577bf03a"
OUT_ISO="$OUT_DIR/Quantic-OS-V1.2-Live-x86_64.iso"

SQUASH_ORIG="$WORK/squashfs.img"
SQUASH_TREE="$WORK/squashfs-root"
SQUASH_NEW="$WORK/squashfs-quantic.img"
ROOT_MNT="$WORK/rootfs-mnt"
QBUILD="$WORK/qbuild"
MOUNTED=0

cleanup() {
  if [[ "$MOUNTED" == 1 ]]; then
    sudo umount "$ROOT_MNT" || true
  fi
}
trap cleanup EXIT

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 2; }; }
for cmd in curl sha256sum xorriso unsquashfs mksquashfs mount umount docker rsync findmnt blkid; do need "$cmd"; done

mkdir -p "$WORK" "$OUT_DIR" "$ROOT_MNT"

echo '[1/8] Downloading the official Fedora KDE 44 Live ISO'
if [[ ! -f "$BASE_ISO" ]]; then
  curl -fL --retry 5 --retry-all-errors --continue-at - "$BASE_URL" -o "$BASE_ISO"
fi
echo "$BASE_SHA256  $BASE_ISO" | sha256sum -c -

echo '[2/8] Building Quantic Home against Fedora 44 Qt 6'
rm -rf "$QBUILD"
mkdir -p "$QBUILD"
docker run --rm \
  -v "$ROOT:/src:ro" \
  -v "$QBUILD:/build" \
  fedora:44 bash -lc '
    set -euxo pipefail
    dnf -y install gcc-c++ cmake ninja-build qt6-qtbase-devel qt6-qtdeclarative-devel qt6-qtsvg-devel
    cmake -S /src/shell -B /build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr
    cmake --build /build --parallel "$(nproc)"
    test -x /build/quantic-home
  '

echo '[3/8] Extracting Fedora LiveOS payload'
rm -rf "$SQUASH_TREE" "$SQUASH_NEW"
xorriso -osirrox on -indev "$BASE_ISO" -extract /LiveOS/squashfs.img "$SQUASH_ORIG" >/dev/null 2>&1
unsquashfs -d "$SQUASH_TREE" "$SQUASH_ORIG" >/dev/null
ROOTFS_IMG="$SQUASH_TREE/LiveOS/rootfs.img"
[[ -f "$ROOTFS_IMG" ]] || { echo 'Fedora LiveOS/rootfs.img not found in squashfs payload' >&2; exit 3; }

FSTYPE=$(blkid -o value -s TYPE "$ROOTFS_IMG" || true)
echo "Root filesystem image type: ${FSTYPE:-unknown}"

echo '[4/8] Mounting and injecting Quantic'
sudo mount -o loop,rw "$ROOTFS_IMG" "$ROOT_MNT"
MOUNTED=1

sudo install -D -m 0755 "$QBUILD/quantic-home" "$ROOT_MNT/usr/libexec/quantic-home"
sudo install -D -m 0644 "$ROOT/shell/autostart/quantic-home.desktop" "$ROOT_MNT/etc/xdg/autostart/quantic-home.desktop"
sudo mkdir -p "$ROOT_MNT/usr/lib/quantic/services" "$ROOT_MNT/etc/quantic"
sudo rsync -a "$ROOT/services/" "$ROOT_MNT/usr/lib/quantic/services/"
sudo rsync -a "$ROOT/config/" "$ROOT_MNT/etc/quantic/"
sudo chmod 0755 "$ROOT_MNT/usr/lib/quantic/services/"*.sh 2>/dev/null || true

# Enable only the early Live USB disk guard at this stage. Other Quantic
# services are kept on disk but are not allowed to make a Live image unbootable.
sudo install -D -m 0644 "$ROOT/systemd/quantic-usb-safe.service" \
  "$ROOT_MNT/usr/lib/systemd/system/quantic-usb-safe.service"
sudo mkdir -p "$ROOT_MNT/etc/systemd/system/local-fs.target.wants"
sudo ln -sfn /usr/lib/systemd/system/quantic-usb-safe.service \
  "$ROOT_MNT/etc/systemd/system/local-fs.target.wants/quantic-usb-safe.service"

# Quantic V1 is Live-only: hide the graphical installer entry points. We do
# not rewrite Fedora's boot chain or kernel; that is precisely what makes this
# remaster path less fragile than rebuilding the distribution from scratch.
sudo mkdir -p "$ROOT_MNT/usr/local/share/applications"
for desktop_id in liveinst.desktop org.fedoraproject.AnacondaInstaller.desktop org.fedoraproject.Anaconda.desktop; do
  sudo tee "$ROOT_MNT/usr/local/share/applications/$desktop_id" >/dev/null <<EOF
[Desktop Entry]
Type=Application
Name=Installer disabled in Quantic Live
Hidden=true
NoDisplay=true
EOF
done

sudo tee "$ROOT_MNT/etc/quantic-release" >/dev/null <<'EOF'
NAME="Quantic OS"
VERSION="1.2 Live"
BASE="Fedora KDE Plasma Desktop 44"
BUILD_STRATEGY="verified-fedora-remaster"
EOF

# Apply Fedora SELinux labels from the target filesystem policy where possible.
sudo chroot "$ROOT_MNT" /sbin/restorecon -RF \
  /usr/libexec/quantic-home \
  /etc/xdg/autostart/quantic-home.desktop \
  /usr/lib/quantic \
  /etc/quantic \
  /usr/lib/systemd/system/quantic-usb-safe.service \
  /usr/local/share/applications 2>/dev/null || true

sync
sudo umount "$ROOT_MNT"
MOUNTED=0

echo '[5/8] Repacking LiveOS squashfs'
mksquashfs "$SQUASH_TREE" "$SQUASH_NEW" -noappend -comp zstd -b 1M >/dev/null

echo '[6/8] Replaying Fedora boot metadata and replacing only LiveOS payload'
rm -f "$OUT_ISO"
xorriso \
  -indev "$BASE_ISO" \
  -outdev "$OUT_ISO" \
  -boot_image any replay \
  -map "$SQUASH_NEW" /LiveOS/squashfs.img \
  -commit >/dev/null 2>&1

echo '[7/8] Structural validation'
test -s "$OUT_ISO"
xorriso -indev "$OUT_ISO" -report_el_torito plain > "$WORK/el-torito.txt" 2>&1
grep -Eqi 'UEFI|EFI|El Torito' "$WORK/el-torito.txt"
xorriso -osirrox on -indev "$OUT_ISO" -extract /LiveOS/squashfs.img "$WORK/verify-squashfs.img" >/dev/null 2>&1
unsquashfs -s "$WORK/verify-squashfs.img" >/dev/null

sha256sum "$OUT_ISO" > "$OUT_ISO.sha256"

echo '[8/8] Done'
ls -lh "$OUT_ISO" "$OUT_ISO.sha256"
echo "Built: $OUT_ISO"
echo 'NOTE: structural build validation is not a physical HP OMEN boot certification.'
