from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_main_uses_quantic_desktop_primitives():
    main = read("shell/qml/Main.qml")
    assert "QBar {" in main
    assert "QSpace {" in main
    assert 'sequence: "Meta+Space"' in main
    assert "backend.activeMission" in main
    assert "backend.restoreActiveMission()" in main
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


def test_phase2_surfaces_exist():
    main = read("shell/qml/Main.qml")
    assert "QuickSettings {" in main
    assert "NotificationCenter {" in main
    assert "QSnap {" in main
    assert 'sequence: "Meta+N"' in main
    assert 'sequence: "Meta+S"' in main


def test_real_app_launcher_is_allowlisted_and_mission_aware():
    header = read("shell/src/Backend.h")
    impl = read("shell/src/Backend.cpp")
    apps = read("shell/qml/pages/AppsPage.qml")
    assert "Q_INVOKABLE bool launchApp" in header
    assert "Q_INVOKABLE int restoreActiveMission" in header
    assert "appCandidates()" in impl
    assert "QStandardPaths::findExecutable" in impl
    assert "QSaveFile" in impl
    assert 'o.insert("missions",missions)' in impl
    assert "m_missionApps" in impl
    assert "backend.launchApp(modelData[2])" in apps
    assert "QProcess::startDetached(exe,{})" in impl
    assert "bash -lc" not in impl[impl.find("bool Backend::launchApp"):impl.find("void Backend::setActiveMission")]


def test_mission_ui_drives_exact_window_snapshot_bridge():
    main = read("shell/qml/Main.qml")
    impl = read("shell/src/Backend.cpp")
    assert 'text: "Enregistrer la Mission"' in main
    assert 'text: "Restaurer la Mission"' in main
    assert "backend.rememberDesktopState()" in main
    assert "backend.restoreActiveMission()" in main
    assert '"capture-state",stateId' in impl
    assert '"restore-state",stateId' in impl
    assert "missionStateId" in impl
    assert "QTimer::singleShot(1600" in impl
    assert "if(!layout.isEmpty())applyWindowLayout(layout)" in impl


def test_quick_settings_are_real_and_allowlisted():
    main = read("shell/src/main.cpp")
    header = read("shell/src/SystemControls.h")
    impl = read("shell/src/SystemControls.cpp")
    qml = read("shell/qml/components/QuickSettings.qml")
    cmake = read("shell/CMakeLists.txt")
    assert 'setContextProperty("systemControls"' in main
    for api in ["setWifiEnabled", "setBluetoothEnabled", "setMuted", "setVolumePercent", "setBrightnessPercent", "cyclePowerProfile"]:
        assert f"Q_INVOKABLE void {api}" in header
        assert f"systemControls.{api}" in qml
    for tool in ["nmcli", "bluetoothctl", "wpctl", "brightnessctl", "powerprofilesctl"]:
        assert f'"{tool}"' in impl
    assert "QStandardPaths::findExecutable" in impl
    assert "bash" not in impl
    assert "sh -c" not in impl
    assert "SystemControls.cpp" in cmake


def test_companion_has_local_push_to_talk_and_orb_presence():
    main_cpp = read("shell/src/main.cpp")
    header = read("shell/src/CompanionBridge.h")
    impl = read("shell/src/CompanionBridge.cpp")
    main_qml = read("shell/qml/Main.qml")
    page = read("shell/qml/pages/CompanionPage.qml")
    orb = read("shell/qml/components/QOrb.qml")
    cmake = read("shell/CMakeLists.txt")
    assert 'setContextProperty("companionBridge"' in main_cpp
    assert "Q_INVOKABLE bool speak" in header
    assert "Q_INVOKABLE bool listenOnce" in header
    assert 'findExecutable({"piper","piper-tts"})' in impl
    assert 'findExecutable({"whisper-cli","whisper-cpp","main"})' in impl
    assert 'findExecutable({"pw-record","arecord"})' in impl
    assert 'findExecutable({"pw-play","aplay"})' in impl
    assert "QTimer::singleShot(6200" in impl
    assert "bash" not in impl and "sh -c" not in impl
    assert "QOrb {" in main_qml
    assert "onHoldVoice: companionBridge.listenOnce()" in main_qml
    assert "companionBridge.speak(backend.companionMessage)" in page
    assert "signal holdVoice()" in orb
    assert "pressAndHoldInterval" in orb
    assert "CompanionBridge.cpp" in cmake and "QOrb.qml" in cmake


def test_cmake_packages_new_shell_components():
    cmake = read("shell/CMakeLists.txt")
    for name in ["QBar.qml", "QSpace.qml", "QuickSettings.qml", "NotificationCenter.qml", "QSnap.qml", "QOrb.qml"]:
        assert f"qml/components/{name}" in cmake
