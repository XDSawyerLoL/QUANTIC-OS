from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_main_uses_quantic_desktop_primitives():
    main = read("shell/qml/Main.qml")
    assert "QBar {" in main
    assert "QSpace {" in main
    assert 'sequence: "Meta+Space"' in main
    assert 'property string activeMission' in main
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


def test_cmake_packages_new_shell_components():
    cmake = read("shell/CMakeLists.txt")
    assert "qml/components/QBar.qml" in cmake
    assert "qml/components/QSpace.qml" in cmake
