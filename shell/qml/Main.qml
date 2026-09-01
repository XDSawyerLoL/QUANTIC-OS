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
    property string activeMission: "Quantic OS"
    property string companionState: "prêt"
    property string lastCommand: ""
    property real uiScale: Math.max(0.82, Math.min(width / 1920, height / 1080))

    Shortcut {
        sequence: "Meta+Space"
        onActivated: qspace.open()
    }
    Shortcut {
        sequence: "Meta+Q"
        onActivated: {
            win.currentPage = "Compagnon"
            win.companionState = "à l'écoute"
        }
    }

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

    // Lightweight desktop header: mission identity, not a permanent dashboard.
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
            MouseArea {
                anchors.fill: parent
                onClicked: missionMenu.open()
            }

            Menu {
                id: missionMenu
                y: parent.height + 6
                MenuItem { text: "Quantic OS"; onTriggered: win.activeMission = text }
                MenuItem { text: "Personnel"; onTriggered: win.activeMission = text }
                MenuItem { text: "Création"; onTriggered: win.activeMission = text }
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
        onCompanion: {
            win.currentPage = "Compagnon"
            win.companionState = "à l'écoute"
        }
    }

    QSpace {
        id: qspace
        uiScale: win.uiScale
        onNavigate: function(page) { win.currentPage = page }
        onRunPrompt: function(prompt) {
            win.lastCommand = prompt
            win.companionState = "en action"
            win.currentPage = "Compagnon"
        }
    }

    // First-run affordance: discoverable without cluttering the desktop.
    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: 26 * win.uiScale
        anchors.topMargin: 22 * win.uiScale
        width: 250 * win.uiScale
        height: 42 * win.uiScale
        radius: 15 * win.uiScale
        color: "#80121925"
        border.color: "#293447"
        z: 20
        Row {
            anchors.centerIn: parent
            spacing: 8 * win.uiScale
            Text { text: "Super + Espace"; color: "#9E95FF"; font.pixelSize: 12 * win.uiScale; font.weight: Font.Medium }
            Text { text: "Q-Space"; color: "#9AA6BA"; font.pixelSize: 12 * win.uiScale }
        }
    }
}