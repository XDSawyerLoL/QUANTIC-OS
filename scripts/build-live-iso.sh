#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUT="$ROOT/build/live"
DESC="$ROOT/build/fedora-kiwi-descriptions"
mkdir -p "$OUT"

command -v kiwi-ng >/dev/null || { echo 'KIWI required on Fedora 44'; exit 2; }
[[ -d "$ROOT/build/rpms/repodata" ]] || "$ROOT/scripts/build-rpms.sh"

rm -rf "$DESC" "$OUT/kiwi" "$OUT/kiwi-build"
# Fedora's release image descriptions. Release branches are preferred; the
# default branch is only a fallback so CI exposes an upstream branch move.
if git clone --depth 1 --branch f44 https://pagure.io/fedora-kiwi-descriptions.git "$DESC"; then
  echo 'Using Fedora KIWI descriptions branch f44'
else
  rm -rf "$DESC"
  git clone --depth 1 https://pagure.io/fedora-kiwi-descriptions.git "$DESC"
  echo 'WARNING: f44 branch unavailable; using repository default branch'
fi

python3 "$ROOT/scripts/prepare-kiwi.py" --description "$DESC" --repo "$ROOT/build/rpms"

# Validate that Quantic was actually injected before starting the expensive build.
grep -q 'repositories/quantic.xml' "$DESC/Fedora.kiwi"
grep -q 'components/quantic.xml' "$DESC/Fedora.kiwi"
grep -q 'quantic.live=1' "$DESC/components/liveinstall.xml"
! grep -q 'anaconda-live' "$DESC/components/liveinstall.xml"

mkdir -p "$OUT/kiwi"
cd "$DESC"
sudo ./kiwi-build \
  --kiwi-file=Fedora.kiwi \
  --image-type=iso \
  --image-profile=KDE-Desktop-Live \
  --image-release=1 \
  --output-dir="$OUT/kiwi"

ISO=$(find "$OUT/kiwi" "$OUT/kiwi-build" -type f -name '*.iso' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n1 | cut -d' ' -f2-)
[[ -n "$ISO" && -f "$ISO" ]] || { echo 'KIWI did not produce an ISO'; exit 4; }
cp -f "$ISO" "$OUT/Quantic-OS-V1.1-Live-x86_64.iso"
sha256sum "$OUT/Quantic-OS-V1.1-Live-x86_64.iso" > "$OUT/Quantic-OS-V1.1-Live-x86_64.iso.sha256"
echo "Built: $OUT/Quantic-OS-V1.1-Live-x86_64.iso"
