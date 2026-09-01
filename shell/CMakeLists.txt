cmake_minimum_required(VERSION 3.24)
project(quantic-home VERSION 1.6 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Qt6 6.5 REQUIRED COMPONENTS Core Gui Quick Qml Svg Network)
qt_standard_project_setup(REQUIRES 6.5)
qt_add_executable(quantic-home
    src/main.cpp
    src/Backend.cpp src/Backend.h
    src/SystemControls.cpp src/SystemControls.h
    src/NotificationBridge.cpp src/NotificationBridge.h
    src/AuthorizationBridge.cpp src/AuthorizationBridge.h
)
qt_add_qml_module(quantic-home
    URI Quantic.Home
    VERSION 1.6
    QML_FILES
        qml/Main.qml
        qml/components/GlassPanel.qml
        qml/components/Sparkline.qml
        qml/components/MetricCard.qml
        qml/components/DockButton.qml
        qml/components/ParticleQ.qml
        qml/components/ResourceRow.qml
        qml/components/QBar.qml
        qml/components/QSpace.qml
        qml/components/QuickSettings.qml
        qml/components/NotificationCenter.qml
        qml/components/QSnap.qml
        qml/components/AuthorizationSheet.qml
        qml/pages/HomePage.qml
        qml/pages/AppsPage.qml
        qml/pages/FilesPage.qml
        qml/pages/CompanionPage.qml
        qml/pages/LabPage.qml
        qml/pages/SettingsPage.qml
        qml/pages/ResourcesPage.qml
    RESOURCES
        qml/assets/icons/home.svg
        qml/assets/icons/apps.svg
        qml/assets/icons/folder.svg
        qml/assets/icons/companion.svg
        qml/assets/icons/lab.svg
        qml/assets/icons/settings.svg
        qml/assets/icons/wifi.svg
        qml/assets/icons/speaker.svg
)
target_link_libraries(quantic-home PRIVATE Qt6::Core Qt6::Gui Qt6::Quick Qt6::Qml Qt6::Svg Qt6::Network)
install(TARGETS quantic-home RUNTIME DESTINATION libexec)
