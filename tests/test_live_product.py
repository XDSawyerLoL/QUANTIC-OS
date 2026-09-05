from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_live_branch_remasters_verified_fedora_kde():
    s = (ROOT / 'scripts/remaster-fedora-kde.sh').read_text()
    assert 'Fedora-KDE-Desktop-Live-44-1.7.x86_64.iso' in s
    assert 'c8295961d4c41adbf785a31a17c21a971d3b7415fda72dcad0c11c49577bf03a' in s
    assert 'boot_image any replay' in s
    assert '/LiveOS/squashfs.img' in s


def test_usb_only_remaster_hides_installer_and_enables_guard():
    s = (ROOT / 'scripts/remaster-fedora-kde.sh').read_text()
    assert 'Hidden=true' in s
    assert 'quantic-usb-safe.service' in s
    assert 'local-fs.target.wants' in s


def test_qml_has_real_pages_and_navigation():
    main = (ROOT / 'shell/qml/Main.qml').read_text()
    assert 'StackLayout' in main
    for name in ['HomePage', 'AppsPage', 'FilesPage', 'CompanionPage', 'LabPage', 'SettingsPage', 'ResourcesPage']:
        assert (ROOT / f'shell/qml/pages/{name}.qml').exists()
        assert name in (ROOT / 'shell/CMakeLists.txt').read_text()


def test_backend_exposes_real_metrics():
    h = (ROOT / 'shell/src/Backend.h').read_text()
    for token in ['cpuHistory', 'gpuHistory', 'ramHistory', 'networkText', 'volumeText', 'safeMode', 'localAiStatus']:
        assert token in h
    cpp = (ROOT / 'shell/src/Backend.cpp').read_text()
    for token in ['/proc/stat', '/proc/meminfo', 'nvidia-smi', 'gpu_busy_percent', 'nmcli', 'wpctl']:
        assert token in cpp


def test_usb_guard_uses_transport_not_only_removable_bit():
    s = (ROOT / 'services/qusb_safe.sh').read_text()
    assert 'lsblk -dn -o NAME,TYPE,TRAN' in s
    assert '"$tran" == "usb"' in s
    assert 'blockdev --setro' in s


def test_live_guard_is_live_gated():
    unit = (ROOT / 'systemd/quantic-usb-safe.service').read_text()
    assert 'rd.live.image' in unit or 'quantic.live=1' in unit


def test_companion_remains_unprivileged():
    unit = (ROOT / 'systemd/user/quantic-companion.service').read_text()
    assert 'NoNewPrivileges=yes' in unit
    assert not (ROOT / 'systemd/quantic-companion.service').exists()


def test_theme_is_plasma6_package():
    metadata = json.loads((ROOT / 'plasma/org.quantic.desktop/metadata.json').read_text())
    assert metadata['KPackageStructure'] == 'Plasma/LookAndFeel'


def test_hosted_ci_is_validation_only():
    w = (ROOT / '.github/workflows/build-live-iso.yml').read_text()
    assert 'Quantic CI' in w
    assert '--privileged' not in w
    assert 'Build-strategy guard' in w


def test_remaster_workflow_builds_and_transports_iso():
    w = (ROOT / '.github/workflows/build-remastered-live.yml').read_text()
    assert 'scripts/remaster-fedora-kde.sh' in w
    assert 'Quantic-OS-V1.2-Live-x86_64.iso.sha256' in w
    assert 'actions/upload-artifact@v4' in w
    assert 'split -b 1800M' in w


def test_rpm_specs_exist():
    for n in ['quantic-shell', 'quantic-services', 'quantic-theme']:
        assert (ROOT / f'rpm/{n}.spec').exists()
