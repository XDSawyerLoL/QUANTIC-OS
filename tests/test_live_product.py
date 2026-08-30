from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def test_live_branch_uses_fedora_kde_kiwi():
    s=(ROOT/'scripts/build-live-iso.sh').read_text(); assert 'fedora-kiwi-descriptions' in s; assert 'KDE-Desktop-Live' in s; assert 'kiwi-build' in s
def test_usb_only_build_removes_installer():
    p=(ROOT/'scripts/prepare-kiwi.py').read_text(); assert 'anaconda-live' in p and 'anaconda-install-env-deps' in p; assert 'quantic.live=1' in p
def test_qml_has_real_pages_and_navigation():
    main=(ROOT/'shell/qml/Main.qml').read_text(); assert 'StackLayout' in main
    for name in ['HomePage','AppsPage','FilesPage','CompanionPage','LabPage','SettingsPage','ResourcesPage']:
        assert (ROOT/f'shell/qml/pages/{name}.qml').exists(); assert name in (ROOT/'shell/CMakeLists.txt').read_text()
def test_backend_exposes_real_metrics():
    h=(ROOT/'shell/src/Backend.h').read_text()
    for token in ['cpuHistory','gpuHistory','ramHistory','networkText','volumeText','safeMode','localAiStatus']: assert token in h
    cpp=(ROOT/'shell/src/Backend.cpp').read_text()
    for token in ['/proc/stat','/proc/meminfo','nvidia-smi','gpu_busy_percent','nmcli','wpctl']: assert token in cpp
def test_usb_guard_uses_transport_not_only_removable_bit():
    s=(ROOT/'services/qusb_safe.sh').read_text(); assert 'lsblk -dn -o NAME,TYPE,TRAN' in s; assert '"$tran" == "usb"' in s; assert 'blockdev --setro' in s
def test_live_guard_is_live_gated():
    unit=(ROOT/'systemd/quantic-usb-safe.service').read_text(); assert 'rd.live.image' in unit or 'quantic.live=1' in unit
def test_companion_remains_unprivileged():
    unit=(ROOT/'systemd/user/quantic-companion.service').read_text(); assert 'NoNewPrivileges=yes' in unit; assert not (ROOT/'systemd/quantic-companion.service').exists()
def test_theme_is_plasma6_package():
    metadata=json.loads((ROOT/'plasma/org.quantic.desktop/metadata.json').read_text()); assert metadata['KPackageStructure']=='Plasma/LookAndFeel'
def test_workflow_builds_and_uploads_iso():
    w=(ROOT/'.github/workflows/build-live-iso.yml').read_text(); assert 'fedora:44' in w; assert '--privileged' in w; assert 'kiwi-systemdeps' in w; assert 'actions/upload-artifact@v4' in w
def test_rpm_specs_exist():
    for n in ['quantic-shell','quantic-services','quantic-theme']: assert (ROOT/f'rpm/{n}.spec').exists()
