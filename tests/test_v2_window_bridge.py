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


def test_wayland_fails_closed_without_kwin(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setattr(qwb, "_qdbus", lambda: None)
    cap = qwb.capability()
    assert cap["can_move_resize"] is False
    assert cap["can_exact_snapshot"] is False
    assert cap["mode"] == "observe-only"


def test_wayland_kwin_enables_native_window_control(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setattr(qwb, "_qdbus", lambda: "/usr/bin/qdbus6")
    monkeypatch.setattr(qwb, "_kwin_available", lambda qdbus=None: True)
    cap = qwb.capability()
    assert cap["can_list"] is False
    assert cap["can_move_resize"] is True
    assert cap["can_exact_snapshot"] is False
    assert cap["mode"] == "wayland-kwin6"


def test_kwin_script_only_uses_known_layout_data():
    script = qwb._kwin_script("half")
    assert "workspace.stackingOrder" in script
    assert "clientArea(KWin.MaximizeArea" in script
    assert "w.frameGeometry" in script
    assert "quantic-home" in script
    assert "eval(" not in script
    assert "callDBus(" not in script


def test_x11_wmctrl_enables_real_window_control(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.setattr(qwb.shutil, "which", lambda name: f"/usr/bin/{name}" if name == "wmctrl" else None)
    cap = qwb.capability()
    assert cap["can_list"] is True
    assert cap["can_move_resize"] is True
    assert cap["can_exact_snapshot"] is True
    assert cap["mode"] == "x11-wmctrl"


def test_state_id_cannot_escape_private_state_root(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANTIC_WINDOW_STATE_DIR", str(tmp_path))
    result = qwb.capture_state("../../etc/passwd")
    assert result == {"ok": False, "error": "invalid-state-id"}
    assert list(tmp_path.iterdir()) == []


def test_capture_state_normalizes_geometry_per_output(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANTIC_WINDOW_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(qwb, "capability", lambda: {"can_exact_snapshot": True, "mode": "x11-wmctrl"})
    monkeypatch.setattr(qwb, "list_outputs", lambda: [
        qwb.Output("DP-1", 0, 0, 1920, 1080),
        qwb.Output("HDMI-1", 1920, 0, 2560, 1440),
    ])
    monkeypatch.setattr(qwb, "list_windows", lambda: [
        qwb.Window("0x1", 1, 42, 2160, 144, 1280, 720, "firefox.Firefox", "Project"),
    ])
    result = qwb.capture_state("creation")
    assert result["ok"] is True
    saved = __import__("json").loads((tmp_path / "creation.json").read_text(encoding="utf-8"))
    window = saved["windows"][0]
    assert window["output"] == "HDMI-1"
    assert window["normalized"] == [0.09375, 0.1, 0.5, 0.5]


def test_restore_state_survives_monitor_resize(monkeypatch, tmp_path):
    monkeypatch.setenv("QUANTIC_WINDOW_STATE_DIR", str(tmp_path))
    payload = {
        "version": 1,
        "state_id": "creation",
        "session": "x11-wmctrl",
        "outputs": [{"name": "DP-1", "x": 0, "y": 0, "width": 1920, "height": 1080}],
        "windows": [{
            "wm_class": "code.Code", "title": "main.cpp", "desktop": 2, "output": "DP-1",
            "geometry": [960, 0, 960, 1080], "normalized": [0.5, 0.0, 0.5, 1.0]
        }],
    }
    (tmp_path / "creation.json").write_text(__import__("json").dumps(payload), encoding="utf-8")
    monkeypatch.setattr(qwb, "capability", lambda: {"can_exact_snapshot": True, "mode": "x11-wmctrl"})
    monkeypatch.setattr(qwb, "list_outputs", lambda: [qwb.Output("DP-1", 0, 0, 2560, 1440)])
    monkeypatch.setattr(qwb, "list_windows", lambda: [qwb.Window("0x9", 2, 77, 10, 10, 800, 600, "code.Code", "main.cpp")])
    calls = []
    monkeypatch.setattr(qwb, "_run", lambda args, timeout=1.5: calls.append(args) or type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    result = qwb.restore_state("creation")
    assert result["ok"] is True
    assert result["restored"] == 1
    geometry_calls = [c for c in calls if "-e" in c]
    assert geometry_calls[-1][-1] == "0,1280,0,1280,1440"


def test_shell_routes_qsnap_through_backend():
    main = (ROOT / "shell" / "qml" / "Main.qml").read_text(encoding="utf-8")
    header = (ROOT / "shell" / "src" / "Backend.h").read_text(encoding="utf-8")
    source = (ROOT / "shell" / "src" / "Backend.cpp").read_text(encoding="utf-8")
    assert "backend.applyWindowLayout(layoutId)" in main
    assert "Q_INVOKABLE void applyWindowLayout" in header
    assert "qwindow_bridge.py" in source
    assert 'static const QStringList allowed={"focus","half","wide","triple"}' in source
