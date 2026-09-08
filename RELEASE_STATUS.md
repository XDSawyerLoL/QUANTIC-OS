# Quantic OS V1.1 Live Product — release status

## Target
A real Fedora KDE 44 Live USB session using Plasma 6 + Wayland for hardware/input/windowing and the Quantic Qt/QML surface for the product experience.

## Current gate
The Fedora remaster, Quantic Home compilation, final ISO generation and SHA-256
verification have completed successfully in CI. Persistent release delivery is
now handled with sub-2-GB GitHub prerelease assets and retry protection. The
image is still not hardware-certified: the real HP Omen acceptance matrix below
remains authoritative.

The release may only be called `V1 Live Candidate` after all of the following are true on real hardware:

- [ ] UEFI Live USB boot succeeds
- [ ] Plasma Wayland session is active
- [ ] native resolution / ultrawide scaling is correct
- [ ] mouse and keyboard work through libinput
- [ ] audio works through PipeWire
- [ ] wired/Wi-Fi networking works through NetworkManager
- [ ] GPU acceleration works on target hardware
- [ ] Quantic Home passes the visual acceptance gate
- [ ] internal non-USB disks are read-only and ignored by UDisks in Live mode
- [ ] companion runs unprivileged
- [ ] Q-Core Bell + CHSH pass
- [ ] Wine/Q-Bridge launches a representative Windows application
- [x] ISO checksum verified after CI build

Framebuffer UI is recovery-only and is not a release acceptance path.
