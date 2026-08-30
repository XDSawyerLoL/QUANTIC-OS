#!/usr/bin/env bash
set -euo pipefail
mkdir -p /run/quantic
: > /run/quantic/protected-disks
while read -r name type tran; do
  [[ "$type" == "disk" ]] || continue
  [[ "$tran" == "usb" ]] && continue
  dev="/dev/$name"
  [[ -b "$dev" ]] || continue
  if /usr/sbin/blockdev --setro "$dev" 2>/dev/null; then
    printf '%s\n' "$dev" >> /run/quantic/protected-disks
  fi
done < <(lsblk -dn -o NAME,TYPE,TRAN | awk '{$1=$1;print}')
printf 'protected\n' > /run/quantic/usb-safe
