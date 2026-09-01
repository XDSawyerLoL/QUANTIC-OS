from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_main_uses_quantic_desktop_primitives():
    main = read("shell/qml/Main.qml")
    assert "QBar {" in main
    assert "QSpace {" in main
    assert "QuickSettings {" in main
    assert "NotificationCenter {" in main
    assert "QSnap {" in main
    assert 'sequence: "Meta+Space"' in main
    assert 'sequence: "Meta+N"' in main
    assert 'sequence: "Meta+S"' in main
    assert 'property string activeMission' in main
    assert 'property string activeLayout' in main
    assert "backend.askCompanion(prompt)" in main
    assert "StackLayout" in main


def test_qbar_is_floating_and_exposes_core_actions():
    qbar = read("shell/qml/components/QBar.qml")
    assert "radius: height / 2" in qbar
    assert "signal commandCenter()" in qbar
    assert "signal companion()" in qbar
    assert 'text: "● Quantic prêt"' in qbar


def test_qspace_is_universal_command_surface():
    qspace = read("shell/qml/components/QSpace.qml")
    assert "signal runPrompt(string prompt)" in qspace
    assert "TextField" in qspace
    assert "Keys.onReturnPressed" in qspace
    assert "SUGGESTIONS" in qspace
    assert "ESPACES" in qspace


def test_phase2_panels_have_escape_and_click_outside_close():
    for path in [
        "shell/qml/components/QuickSettings.qml",
        "shell/qml/components/NotificationCenter.qml",
        "shell/qml/components/QSnap.qml",
    ]:
        content = read(path)
        assert "Popup.CloseOnEscape" in content
        assert "Popup.CloseOnPressOutside" in content


def test_qsnap_exposes_layout_choice_without_direct_privilege():
    snap = read("shell/qml/components/QSnap.qml")
    assert "signal layoutChosen(string layoutId)" in snap
    assert '"split"' in snap
    assert '"focus"' in snap
    assert '"triple"' in snap
    assert "backend" not in snap


def test_cmake_packages_new_shell_components():
    cmake = read("shell/CMakeLists.txt")
    for path in [
        "qml/components/QBar.qml",
        "qml/components/QSpace.qml",
        "qml/components/QuickSettings.qml",
        "qml/components/NotificationCenter.qml",
        "qml/components/QSnap.qml",
    ]:
        assert path in cmake
