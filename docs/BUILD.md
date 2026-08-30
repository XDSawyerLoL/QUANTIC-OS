# Build Quantic OS Live

## Supported build path
The supported V1.1 build runs on a Fedora 44 environment with `livecd-tools` and the Fedora KDE spin kickstart.

```bash
sudo dnf install livecd-tools spin-kickstarts pykickstart rpm-build createrepo_c \
  gcc-c++ cmake ninja-build qt6-qtbase-devel qt6-qtdeclarative-devel qt6-qtsvg-devel
./scripts/build-rpms.sh
./scripts/build-live-iso.sh
```

The GitHub Actions workflow `.github/workflows/build-live-iso.yml` runs the same process in a privileged Fedora 44 container and uploads the ISO as a workflow artifact.

A successful ISO build is only the build gate. Real hardware acceptance is tracked in `docs/ACCEPTANCE.md`.
