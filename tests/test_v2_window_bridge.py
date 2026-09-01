import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("qwindow_bridge", ROOT / "services" / "qwindow_bridge.py")
assert SPEC and SPEC.loader
qwb = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qwb
SPEC.loader.exec_module(qwb)


def test_layouts_are_bounded_and_known():
    assert set(qwb.LAYOUTS) == {"focus", "half", "wide", "triple"}
    for slots in qwb.LAYOUTS.values():
        for x, y, w, h in slots:
            assert 0 <= x <= 1
            assert 0 <= y <= 1
            assert 0 < w <= 1
            assert 0 < h <= 1
            assert x + w <= 1.001
            assert y + h <= 1.001


def test_unknown_layout_is_refused():
    result = qwb.apply_layout("arbitrary-shell-command")
    assert result["ok"] is False
    assert result["error"] == "unknown-layout"


def test_wayland_fails_closed(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setattr(qwb.shutil, "which", lambda _: "/usr/bin/wmctrl")
    cap = qwb.capability()
    assert cap["can_move_resize"] is False
    assert cap["mode"] == "observe-only"


def test_x11_wmctrl_enables_real_window_control(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.setattr(qwb.shutil, "which", lambda name: f"/usr/bin/{name}" if name == "wmctrl" else None)
    cap = qwb.capability()
    assert cap["can_list"] is True
    assert cap["can_move_resize"] is True
    assert cap["mode"] == "x11-wmctrl"


def test_shell_routes_qsnap_through_backend():
    main = (ROOT / "shell" / "qml" / "Main.qml").read_text(encoding="utf-8")
    header = (ROOT / "shell" / "src" / "Backend.h").read_text(encoding="utf-8")
    source = (ROOT / "shell" / "src" / "Backend.cpp").read_text(encoding="utf-8")
    assert "backend.applyWindowLayout(layoutId)" in main
    assert "Q_INVOKABLE void applyWindowLayout" in header
    assert "qwindow_bridge.py" in source
    assert 'static const QStringList allowed={"focus","half","wide","triple"}' in source
