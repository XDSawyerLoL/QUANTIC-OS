# Quantic OS V1 build strategy

## Why the previous pipeline is being retired

The previous GitHub Actions job tried to build an entire Fedora KDE Live ISO from Fedora KIWI descriptions inside a privileged Fedora container running on an Ubuntu GitHub host. That combines three moving parts at once: Ubuntu's host kernel/runtime, a Fedora container, and Fedora's release image-composition tooling.

For a first physically testable Quantic V1 this is unnecessary risk. The product layer should be tested separately from Fedora's release-engineering layer.

## V1.2 strategy: verified Fedora remaster

Quantic V1.2 starts from the official Fedora KDE Plasma Desktop 44 x86_64 Live ISO.

The pipeline:

1. downloads the exact Fedora 44 KDE release ISO;
2. verifies Fedora's published SHA-256 before touching it;
3. builds `quantic-home` against Fedora 44 / Qt 6 in a Fedora 44 build container;
4. extracts only the `LiveOS` payload;
5. injects Quantic Home, configuration, services and the Live USB disk guard;
6. hides graphical installer entry points because this milestone is Live-only;
7. recreates only the LiveOS squashfs;
8. uses xorriso's boot-image replay mode so Fedora's proven BIOS/UEFI boot metadata is preserved instead of being re-authored by Quantic;
9. validates the resulting ISO structure and writes a SHA-256 file.

This deliberately avoids rebuilding Fedora's kernel, initramfs, GRUB/shim and live boot chain for the first V1 hardware milestone.

## CI split

`build-live-iso.yml` is now CI only. It performs source, Python and shell validation on GitHub-hosted runners.

`build-remastered-live.yml` performs the large ISO remaster. It can run on GitHub-hosted Ubuntu because the distribution image is no longer composed there: the official Fedora ISO is the bootable base and only its LiveOS payload is replaced.

## Security / Live-only scope

`quantic-usb-safe.service` is enabled in the remaster and is gated by Fedora's Live boot command line. It marks non-USB whole disks read-only before the normal desktop storage stack starts. This is a conservative safety mechanism, not a forensic write-blocking guarantee.

The V1.2 image is not an installer. Installer launchers are hidden in the remaster. A later installable edition must be a separate product with explicit disk selection, confirmation and rollback design.

## Acceptance gate

An ISO is not called a Quantic V1 release merely because CI produced a file. Release status requires, in order:

- Fedora base checksum verified;
- Quantic Home compiled successfully on Fedora 44;
- ISO BIOS/UEFI boot metadata structurally present;
- LiveOS squashfs readable after rebuild;
- output SHA-256 generated and verified;
- VM boot test when available;
- physical HP OMEN boot test;
- keyboard, mouse, display, GPU, audio, network and internal-disk safety checks;
- real runtime screenshot compared with the approved Quantic visual target.

Only after the first stable hardware milestone do we return to the atomic Kinoite/bootc delivery layer. Atomic updates remain the production goal; they are no longer allowed to block first-boot validation.
