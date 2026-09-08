# Quantic OS V1.1 — Live Product

Quantic OS is now built as a **Fedora KDE 44 Live USB product**, not a custom framebuffer shell.

Official repository: `XDSawyerLoL/QUANTIC-OS`.

The canonical delivery branch is `main`. Successful delivery builds publish a
persistent GitHub prerelease containing sub-2-GB ISO parts, checksums and the
Windows reassembly instructions. A green source test alone is not a hardware
certification.

## Product stack
- Fedora KDE 44 Live base
- Plasma 6 + KWin + Wayland
- libinput / PipeWire / NetworkManager / UDisks
- Quantic Home: native Qt 6 / QML surface
- Q-Companion: local-first, unprivileged agent
- Q-Model Hub / Ollama local runtime (no API key required for standard use)
- Q-Core / Q-Bridge / Q-Resource / Q-Guardian
- Q-USB Guard: independent Live-storage protection

## Build
On Fedora 44:
```bash
sudo dnf install livecd-tools spin-kickstarts pykickstart rpm-build createrepo_c gcc-c++ cmake ninja-build qt6-qtbase-devel qt6-qtdeclarative-devel qt6-qtsvg-devel
./scripts/build-rpms.sh
./scripts/build-live-iso.sh
```
Or use `.github/workflows/build-live-iso.yml`.

## USB-only rule
The kickstart removes Anaconda/liveinst. In Live mode Q-USB Guard sets non-USB whole disks read-only before UDisks; UDisks also ignores internal storage.

## Release discipline
A successful build does not equal a released product. See `RELEASE_STATUS.md`.
