#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd);OUT="$ROOT/build/live";mkdir -p "$OUT"
command -v livecd-creator >/dev/null || { echo 'livecd-tools required on Fedora 44'; exit 2; }
command -v ksflatten >/dev/null || { echo 'pykickstart required'; exit 2; }
[[ -d "$ROOT/build/rpms/repodata" ]] || "$ROOT/scripts/build-rpms.sh"
BASE=${BASE_KS:-/usr/share/spin-kickstarts/fedora-live-kde.ks};[[ -f "$BASE" ]] || { echo "Missing $BASE";exit 3; }
ksflatten -c "$BASE" -o "$OUT/fedora-kde-flat.ks"
python3 "$ROOT/scripts/generate-kickstart.py" --base "$OUT/fedora-kde-flat.ks" --repo "$ROOT/build/rpms" --out "$OUT/quantic-live.ks"
cd "$OUT"
sudo livecd-creator --verbose --config="$OUT/quantic-live.ks" --fslabel=QUANTIC-OS --releasever=44 --cache="$OUT/cache"
ISO=$(find "$OUT" -maxdepth 1 -type f -name '*.iso' -printf '%T@ %p\n' | sort -nr | head -n1 | cut -d' ' -f2-)
[[ -n "$ISO" && -f "$ISO" ]] || { echo 'ISO was not produced';exit 4; }
mv -f "$ISO" "$OUT/Quantic-OS-V1.1-Live-x86_64.iso" 2>/dev/null || true
sha256sum "$OUT/Quantic-OS-V1.1-Live-x86_64.iso" > "$OUT/Quantic-OS-V1.1-Live-x86_64.iso.sha256"
