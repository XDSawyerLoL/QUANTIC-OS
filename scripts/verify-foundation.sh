#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

python3 -m py_compile services/*.py scripts/*.py
bash -n scripts/*.sh services/*.sh
python3 -m pytest -q

test -f scripts/remaster-fedora-kde.sh
test -f .github/workflows/build-remastered-live.yml
grep -q 'Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso' scripts/remaster-fedora-kde.sh
grep -q 'BASE_SHA256=' scripts/remaster-fedora-kde.sh
grep -q 'boot_image any replay' scripts/remaster-fedora-kde.sh
grep -q 'StackLayout' shell/qml/Main.qml
grep -q 'lsblk -dn -o NAME,TYPE,TRAN' services/qusb_safe.sh

echo 'Quantic V1.2 foundation verification: PASS'
