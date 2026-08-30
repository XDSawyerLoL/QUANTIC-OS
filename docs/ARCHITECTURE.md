# Architecture — Live product branch

```text
UEFI firmware
    |
Fedora KDE 44 Live boot chain
    |
Linux kernel + DRM/KMS + libinput
    |
KWin + Wayland + Plasma 6
    |
Quantic Home (Qt 6 / QML, fullscreen product surface)
    |
+----------------------------------+
| Q-Companion | Q-Resource         |
| Q-Bridge    | Q-Hardware         |
| Q-Core      | Q-Explain          |
| Q-Model Hub | Q-Permission       |
+----------------------------------+
    |
PipeWire | NetworkManager | UDisks | Wine | Ollama
```

## Why Plasma/KWin first
KWin and Plasma already solve input, multi-monitor, HiDPI, window management, Wayland security boundaries and desktop plumbing. Quantic owns the experience above that layer. Replacing the compositor is not a V1 goal.

## Live USB branch
The V1 Live branch is deliberately based on Fedora KDE Live rather than an installable atomic desktop. It must boot and operate from USB without installing Quantic to internal storage. Internal non-USB disks are protected by Q-USB Guard and hidden from UDisks in normal Live mode.

## Future installable branch
An installable/atomic edition may later use bootc/ostree-style deployments and rollback. It is a separate release track and must not compromise the USB-only safety contract.

## Resource adaptation
Q-Resource classifies the current workload and produces reversible plans. Custom sched_ext policies remain experimental until hardware-specific benchmarks prove an advantage.
