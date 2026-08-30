#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUT="$ROOT/build/rpms"; TOP="$ROOT/build/rpmbuild"
rm -rf "$OUT" "$TOP"; mkdir -p "$OUT" "$TOP"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
version=1.1.0
make_src(){ local pkg=$1;shift;local tmp;tmp=$(mktemp -d);mkdir -p "$tmp/$pkg-$version";for path in "$@";do cp -a "$ROOT/$path" "$tmp/$pkg-$version/";done;tar -C "$tmp" -czf "$TOP/SOURCES/$pkg-$version.tar.gz" "$pkg-$version";rm -rf "$tmp";cp "$ROOT/rpm/$pkg.spec" "$TOP/SPECS/";rpmbuild --define "_topdir $TOP" -ba "$TOP/SPECS/$pkg.spec";}
make_src quantic-shell shell
make_src quantic-services services systemd udev polkit
make_src quantic-theme plasma assets
find "$TOP/RPMS" -name '*.rpm' -exec cp -v {} "$OUT/" \;
createrepo_c "$OUT"
echo "RPM repository: $OUT"
