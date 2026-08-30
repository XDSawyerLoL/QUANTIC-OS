from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]

def test_visual_reference_is_present():
    assert (ROOT/'assets/quantic-wallpaper.svg').stat().st_size > 500

def test_live_product_has_real_plasma_wayland_build_path():
    text=(ROOT/'scripts/build-live-iso.sh').read_text()
    assert 'fedora-kiwi-descriptions' in text
    assert 'KDE-Desktop-Live' in text
    assert 'kiwi-build' in text

def test_normal_shell_is_qml_not_framebuffer():
    qml=(ROOT/'shell/qml/Main.qml').read_text()
    assert 'ApplicationWindow' in qml
    assert 'Window.FullScreen' in qml
    assert 'framebuffer' not in qml.lower()

def test_policy_has_hard_denies():
    p=json.loads((ROOT/'config/permissions.json').read_text())
    assert 'security.disable' in p['deny']
    assert 'update.bypass_guardian' in p['deny']
    assert 'boot.disable_rollback' in p['deny']

def test_usb_safe_is_kernel_cmdline_gated():
    unit=(ROOT/'systemd/quantic-usb-safe.service').read_text()
    assert 'quantic.live=1' in unit or 'rd.live.image' in unit

def test_companion_is_user_service_not_root_daemon():
    assert (ROOT/'systemd/user/quantic-companion.service').exists()
    assert not (ROOT/'systemd/quantic-companion.service').exists()
