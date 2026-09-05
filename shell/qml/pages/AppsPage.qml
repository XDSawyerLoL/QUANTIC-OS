import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quantic.Home

Item {
    id: root
    property real unit: Math.max(0.8, Math.min(width / 1920, height / 1080))

    Column {
        x: 54 * root.unit
        y: 38 * root.unit
        spacing: 8 * root.unit
        Text { text: "Applications"; color: "white"; font.pixelSize: 34 * root.unit; font.weight: Font.Light }
        Text { text: "Lanceur natif · Quantic utilise uniquement des applications autorisées et installées localement."; color: "#9EAAC0"; font.pixelSize: 14 * root.unit }
    }

    Grid {
        x: 54 * root.unit
        y: 132 * root.unit
        columns: 3
        spacing: 16 * root.unit

        Repeater {
            model: [
                ["Navigateur", "Web et outils en ligne", "browser", "◎"],
                ["Fichiers", "Documents et espaces de travail", "files", "▤"],
                ["Terminal", "Shell et diagnostics", "terminal", ">_"],
                ["Éditeur", "Code, texte et projets", "editor", "{}"],
                ["Paramètres", "Écrans, réseau, son et périphériques", "settings", "⚙"],
                ["Logiciels", "Applications Fedora et Flatpak", "discover", "▦"]
            ]

            Rectangle {
                width: 318 * root.unit
                height: 142 * root.unit
                radius: 22 * root.unit
                color: mouse.containsMouse ? "#D0151D2A" : "#A5101722"
                border.color: mouse.containsMouse ? "#596A85" : "#2B3648"

                Row {
                    anchors.fill: parent
                    anchors.margins: 20 * root.unit
                    spacing: 16 * root.unit
                    Rectangle {
                        width: 48 * root.unit; height: width; radius: 15 * root.unit
                        color: "#1B2440"
                        Text { anchors.centerIn: parent; text: modelData[3]; color: "#AAA2FF"; font.pixelSize: 18 * root.unit; font.weight: Font.DemiBold }
                    }
                    Column {
                        width: 205 * root.unit
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 6 * root.unit
                        Text { text: modelData[0]; color: "#F3F5FA"; font.pixelSize: 17 * root.unit; font.weight: Font.DemiBold }
                        Text { text: modelData[1]; width: parent.width; wrapMode: Text.WordWrap; color: "#8F9CB0"; font.pixelSize: 12 * root.unit }
                    }
                }
                MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; onClicked: backend.launchApp(modelData[2]) }
            }
        }
    }

    Rectangle {
        x: 54 * root.unit
        y: 452 * root.unit
        width: 986 * root.unit
        height: 58 * root.unit
        radius: 18 * root.unit
        color: "#80101722"
        border.color: "#283447"
        Row {
            anchors.fill: parent
            anchors.leftMargin: 18 * root.unit
            anchors.rightMargin: 18 * root.unit
            spacing: 12 * root.unit
            Text { anchors.verticalCenter: parent.verticalCenter; text: "État"; color: "#7F8BA0"; font.pixelSize: 12 * root.unit }
            Text { anchors.verticalCenter: parent.verticalCenter; text: backend.lastLaunchStatus; color: "#CBD3E0"; font.pixelSize: 12 * root.unit }
            Item { width: 1; height: 1 }
        }
    }
}
