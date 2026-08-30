#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); cd "$ROOT"
python3 -m py_compile services/*.py scripts/generate-kickstart.py
bash -n scripts/build-rpms.sh scripts/build-live-iso.sh services/qusb_safe.sh
pytest -q
grep -q 'fedora-live-kde.ks' scripts/build-live-iso.sh
grep -q 'StackLayout' shell/qml/Main.qml
grep -q 'lsblk -dn -o NAME,TYPE,TRAN' services/qusb_safe.sh
echo 'Quantic V1.1 foundation verification: PASS'
