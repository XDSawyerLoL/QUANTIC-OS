#!/usr/bin/env bash
set -Eeuo pipefail

ASSET_DIR=${1:-build/live}
ISO_NAME=Quantic-OS-Final-Live-x86_64.iso
REPOSITORY=${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}
SOURCE_SHA=${GITHUB_SHA:?GITHUB_SHA is required}
SHORT_SHA=${SOURCE_SHA:0:12}
TAG=${QUANTIC_RELEASE_TAG:-quantic-v2-${SHORT_SHA}}
TITLE="Quantic OS V2 Developer Preview ${SHORT_SHA}"
NOTES="$ASSET_DIR/RELEASE-NOTES.md"

command -v gh >/dev/null 2>&1 || {
  echo 'GitHub CLI is required to publish the Quantic ISO.' >&2
  exit 2
}

mapfile -t PARTS < <(find "$ASSET_DIR" -maxdepth 1 -type f -name "${ISO_NAME}.part-*" -print | sort)
(( ${#PARTS[@]} > 0 )) || {
  echo "No split ISO parts found in $ASSET_DIR" >&2
  exit 3
}

REQUIRED=(
  "$ASSET_DIR/${ISO_NAME}.sha256"
  "$ASSET_DIR/${ISO_NAME%.iso}.parts.sha256"
  "$ASSET_DIR/BUILD-MANIFEST.txt"
  "$ASSET_DIR/REASSEMBLE-WINDOWS.txt"
  "$ASSET_DIR/prepare-quantic-data.ps1"
  "$ASSET_DIR/QUANTIC-DATA-README.txt"
)

for file in "${PARTS[@]}" "${REQUIRED[@]}"; do
  [[ -s "$file" ]] || {
    echo "Missing or empty release asset: $file" >&2
    exit 4
  }
done

# GitHub release assets must remain below 2 GB. The workflow creates 1500 MiB
# chunks; this guard prevents a future split-size edit from silently breaking
# delivery after the expensive ISO build has completed.
for part in "${PARTS[@]}"; do
  size=$(stat -c '%s' "$part")
  (( size < 2000000000 )) || {
    echo "Release part exceeds the 2 GB transport ceiling: $part ($size bytes)" >&2
    exit 5
  }
done

cat > "$NOTES" <<EOF
# Quantic OS V2 Developer Preview

- Source commit: \`${SOURCE_SHA}\`
- Fedora base: Fedora KDE Plasma Desktop 44
- Delivery: split ISO with whole-image and per-part SHA-256 checksums
- Runtime: Quantic Home, local voice, Ollama runtime and USB-only QUANTIC-DATA persistence

This is a hardware acceptance candidate, not a certified final release. Reassemble every part, verify \`${ISO_NAME}.sha256\`, then flash the ISO. The HP Omen keyboard, mouse, display, NVIDIA, audio, network and internal-disk protection checks remain mandatory.
EOF

if ! gh release view "$TAG" --repo "$REPOSITORY" >/dev/null 2>&1; then
  gh release create "$TAG" \
    --repo "$REPOSITORY" \
    --target "$SOURCE_SHA" \
    --title "$TITLE" \
    --notes-file "$NOTES" \
    --prerelease
fi

ASSETS=("${PARTS[@]}" "${REQUIRED[@]}" "$NOTES")
for attempt in 1 2 3; do
  if gh release upload "$TAG" "${ASSETS[@]}" --repo "$REPOSITORY" --clobber; then
    break
  fi
  if (( attempt == 3 )); then
    echo 'Release upload failed after three attempts.' >&2
    exit 6
  fi
  echo "Release upload attempt $attempt failed; retrying." >&2
  sleep $((attempt * 10))
done

REMOTE_NAMES=$(gh release view "$TAG" --repo "$REPOSITORY" --json assets --jq '.assets[].name')
for file in "${ASSETS[@]}"; do
  name=$(basename "$file")
  grep -Fxq "$name" <<<"$REMOTE_NAMES" || {
    echo "Release verification failed; remote asset is missing: $name" >&2
    exit 7
  }
done

echo "Published persistent Quantic prerelease: $TAG"
