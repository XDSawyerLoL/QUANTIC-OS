# V1 Release Acceptance

A candidate is rejected unless every critical item passes.

## Boot and hardware

- [ ] UEFI boot on HP Omen reference PC.
- [ ] Secure Boot path documented; signed production path before final release.
- [ ] mouse/keyboard operational before login/home.
- [ ] native monitor resolution and ultrawide scaling.
- [ ] NVIDIA/AMD/Intel GPU driver status visible.
- [ ] audio output/input enumerated.
- [ ] Ethernet/Wi-Fi/Bluetooth enumerated.

## UI

- [ ] Quantic Home uses production Qt/QML, not framebuffer recovery.
- [ ] visual regression screenshot at 3440x1440 reviewed against approved reference.
- [ ] dock is interactive.
- [ ] all six primary destinations open real destinations.
- [ ] no debug text or terminal echo in normal mode.

## Data integrity

- [ ] CPU/RAM metrics measured.
- [ ] GPU metric measured or displayed as unavailable.
- [ ] USB-safe mode does not auto-mount internal Windows disks.
- [ ] removing USB and rebooting returns to the host OS unchanged.

## Companion and autonomy

- [ ] local model route works without API key when a local model is installed.
- [ ] companion memory persists on the USB persistence volume.
- [ ] ALLOW/ASK/DENY capabilities enforced outside the model.
- [ ] explanation log records autonomous resource changes.

## Update

- [ ] update is staged atomically.
- [ ] failed health check can roll back.
- [ ] user can boot previous deployment.
