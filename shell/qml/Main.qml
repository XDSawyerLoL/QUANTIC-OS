import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import Quantic.Home

ApplicationWindow {
    id: win
    visible: true
    visibility: Window.FullScreen
    color: "#04070D"
    title: "Quantic OS"

    property string currentPage: "Accueil"
    property string activeMission: backend.activeMission
    property string companionState: "prêt"
    property string lastCommand: ""
    property string activeLayout: "focus"
    property real uiScale: Math.max(0.82, Math.min(width / 1920, height / 1080))

    Shortcut { sequence: "Meta+Space"; onActivated: qspace.open() }
    Shortcut { sequence: "Meta+Q"; onActivated: { win.currentPage = "Compagnon"; win.companionState = "à l'écoute" } }
    Shortcut { sequence: "Meta+N"; onActivated: notifications.open() }
    Shortcut { sequence: "Meta+S"; onActivated: qsnap.open() }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#03070C" }
            GradientStop { position: 0.46; color: "#07101B" }
            GradientStop { position: 1.0; color: "#04070D" }
        }
    }

    Rectangle {
        width: parent.width * 0.64
        height: parent.height * 0.72
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        radius: height / 2
        color: "#243067"
        opacity: 0.07
        layer.enabled: true
        layer.effect: MultiEffect { blurEnabled: true; blur: 1.0; blurMax: 64 }
    }

    RowLayout {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: 28 * win.uiScale
        anchors.topMargin: 22 * win.uiScale
        spacing: 10 * win.uiScale
        z: 20

        Rectangle {
            Layout.preferredWidth: 185 * win.uiScale
            Layout.preferredHeight: 42 * win.uiScale
            radius: 15 * win.uiScale
            color: "#A6121925"
            border.color: "#2F3A4D"
            Row {
                anchors.centerIn: parent
                spacing: 9 * win.uiScale
                Rectangle { width: 8 * win.uiScale; height: width; radius: width / 2; color: "#8177FF" }
                Text { text: win.activeMission; color: "#E8ECF5"; font.pixelSize: 13 * win.uiScale; font.weight: Font.Medium }
                Text { text: "⌄"; color: "#7F8BA0"; font.pixelSize: 12 * win.uiScale }
            }
            MouseArea { anchors.fill: parent; onClicked: missionMenu.open() }
            Menu {
                id: missionMenu
                y: parent.height + 6
                MenuItem { text: "Quantic OS"; onTriggered: backend.setActiveMission(text) }
                MenuItem { text: "Personnel"; onTriggered: backend.setActiveMission(text) }
                MenuItem { text: "Création"; onTriggered: backend.setActiveMission(text) }
                MenuSeparator { }
                MenuItem { text: "Restaurer les applications"; onTriggered: backend.restoreActiveMission() }
                MenuItem { text: "Enregistrer l’état"; onTriggered: backend.rememberDesktopState() }
            }
        }

        Rectangle {
            visible: win.lastCommand.length > 0
            Layout.preferredWidth: Math.min(activityText.implicitWidth + 34 * win.uiScale, 510 * win.uiScale)
            Layout.preferredHeight: 42 * win.uiScale
            radius: 15 * win.uiScale
            color: "#A6121925"
            border.color: "#2F3A4D"
            Text {
                id: activityText
                anchors.centerIn: parent
                width: parent.width - 24 * win.uiScale
                elide: Text.ElideRight
                text: "● Quantic — " + win.lastCommand
                color: "#ABB6C9"
                font.pixelSize: 12 * win.uiScale
            }
        }
    }

    Row {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: 26 * win.uiScale
        anchors.topMargin: 22 * win.uiScale
        spacing: 8 * win.uiScale
        z: 25

        Rectangle {
            visible: backend.windowBridgeStatus.length > 0
            width: 205 * win.uiScale
            height: 42 * win.uiScale
            radius: 15 * win.uiScale
            color: "#80121925"
            border.color: "#293447"
            Text {
                anchors.centerIn: parent
                width: parent.width - 20 * win.uiScale
                elide: Text.ElideRight
                text: backend.windowBridgeStatus
                color: "#8E9AAF"
                font.pixelSize: 11 * win.uiScale
            }
            MouseArea { anchors.fill: parent; onClicked: backend.refreshWindowBridge() }
        }

        Repeater {
            model: [["▦","Q‑Snap"],["●","Notifications"],["⌁","Réglages"]]
            delegate: Rectangle {
                width: modelData[1] === "Réglages" ? 118 * win.uiScale : 46 * win.uiScale
                height: 42 * win.uiScale
                radius: 15 * win.uiScale
                color: hover.containsMouse ? "#CC182131" : "#80121925"
                border.color: hover.containsMouse ? "#4A5970" : "#293447"
                Row {
                    anchors.centerIn: parent
                    spacing: 7 * win.uiScale
                    Text { text: modelData[0]; color: "#AAA2FF"; font.pixelSize: 13 * win.uiScale }
                    Text { visible: modelData[1] === "Réglages"; text: Qt.formatDateTime(new Date(), "HH:mm"); color: "#D4DBE7"; font.pixelSize: 12 * win.uiScale }
                }
                MouseArea {
                    id: hover
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        if (modelData[1] === "Q‑Snap") qsnap.open()
                        else if (modelData[1] === "Notifications") notifications.open()
                        else quickSettings.open()
                    }
                }
            }
        }
    }

    StackLayout {
        id: pages
        anchors.fill: parent
        anchors.topMargin: 66 * win.uiScale
        anchors.bottomMargin: 94 * win.uiScale
        currentIndex: ["Accueil", "Apps", "Fichiers", "Compagnon", "Lab", "Paramètres", "Ressources"].indexOf(win.currentPage)
        HomePage { onNavigate: function(page) { win.currentPage = page } }
        AppsPage { }
        FilesPage { }
        CompanionPage { }
        LabPage { }
        SettingsPage { }
        ResourcesPage { }
    }

    QBar {
        id: qbar
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 18 * win.uiScale
        uiScale: win.uiScale
        currentPage: win.currentPage
        z: 50
        onNavigate: function(page) { win.currentPage = page }
        onCommandCenter: qspace.open()
        onCompanion: { win.currentPage = "Compagnon"; win.companionState = "à l'écoute" }
    }

    QSpace {
        id: qspace
        uiScale: win.uiScale
        onNavigate: function(page) { win.currentPage = page }
        onRunPrompt: function(prompt) {
            win.lastCommand = prompt
            win.companionState = "en action"
            backend.askCompanion(prompt)
            win.currentPage = "Compagnon"
        }
    }

    QuickSettings {
        id: quickSettings
        uiScale: win.uiScale
        x: win.width - width - 26 * win.uiScale
        y: 72 * win.uiScale
        z: 100
    }

    NotificationCenter {
        id: notifications
        uiScale: win.uiScale
        x: win.width - width - 26 * win.uiScale
        y: 72 * win.uiScale
        z: 100
    }

    QSnap {
        id: qsnap
        uiScale: win.uiScale
        x: win.width - width - 26 * win.uiScale
        y: 72 * win.uiScale
        z: 100
        onLayoutChosen: function(layoutId) {
            win.activeLayout = layoutId
            win.lastCommand = "Disposition Q‑Snap · " + layoutId
            backend.applyWindowLayout(layoutId)
        }
    }
}
