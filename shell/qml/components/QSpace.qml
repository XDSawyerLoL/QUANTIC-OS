import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root
    property real uiScale: 1.0
    signal navigate(string page)
    signal runPrompt(string prompt)

    modal: true
    focus: true
    width: Math.min(parent ? parent.width * 0.70 : 980, 1040 * uiScale)
    height: 520 * uiScale
    anchors.centerIn: Overlay.overlay
    padding: 0
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    background: Rectangle {
        radius: 28 * root.uiScale
        color: "#F0121825"
        border.color: "#46526B"
        border.width: 1
    }

    onOpened: search.forceActiveFocus()

    contentItem: ColumnLayout {
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 86 * root.uiScale
            Layout.leftMargin: 22 * root.uiScale
            Layout.rightMargin: 22 * root.uiScale
            spacing: 14 * root.uiScale

            Text { text: "Q"; color: "#A79FFF"; font.pixelSize: 28 * root.uiScale; font.weight: Font.Bold }
            TextField {
                id: search
                Layout.fillWidth: true
                placeholderText: "Ouvrir, rechercher, agir ou demander à Quantic…"
                color: "#F4F6FA"
                placeholderTextColor: "#77839A"
                font.pixelSize: 19 * root.uiScale
                background: Rectangle { color: "transparent" }
                Keys.onReturnPressed: {
                    if (text.trim().length > 0) {
                        root.runPrompt(text.trim())
                        root.close()
                    }
                }
            }
            Text { text: "Esc"; color: "#77839A"; font.pixelSize: 11 * root.uiScale }
        }

        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: "#2B3548" }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 22 * root.uiScale
            spacing: 24 * root.uiScale

            ColumnLayout {
                Layout.preferredWidth: 270 * root.uiScale
                Layout.fillHeight: true
                spacing: 8 * root.uiScale
                Text { text: "ESPACES"; color: "#717E95"; font.pixelSize: 11 * root.uiScale; font.letterSpacing: 1.2 }
                Repeater {
                    model: [
                        ["Accueil", "Vue du système"],
                        ["Apps", "Applications"],
                        ["Fichiers", "Documents et projets"],
                        ["Compagnon", "Quantic Companion"],
                        ["Lab", "Outils avancés"],
                        ["Paramètres", "Réglages système"]
                    ]
                    Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 52 * root.uiScale
                        radius: 13 * root.uiScale
                        color: area.containsMouse ? "#202B3F" : "transparent"
                        Row {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 12 * root.uiScale
                            spacing: 10 * root.uiScale
                            Text { text: modelData[0]; color: "#E7EBF4"; font.pixelSize: 14 * root.uiScale }
                            Text { text: modelData[1]; color: "#758197"; font.pixelSize: 11 * root.uiScale }
                        }
                        MouseArea {
                            id: area
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: { root.navigate(modelData[0]); root.close() }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }

            Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#2B3548" }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12 * root.uiScale
                Text { text: "SUGGESTIONS"; color: "#717E95"; font.pixelSize: 11 * root.uiScale; font.letterSpacing: 1.2 }
                Repeater {
                    model: [
                        "Reprendre mon dernier projet",
                        "Organiser mon espace de travail",
                        "Pourquoi mon PC rame ?",
                        "Trouver mes fichiers récents"
                    ]
                    Rectangle {
                        required property string modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 66 * root.uiScale
                        radius: 16 * root.uiScale
                        color: hintArea.containsMouse ? "#202A3D" : "#171F2E"
                        border.color: "#2D394F"
                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16 * root.uiScale
                            anchors.rightMargin: 16 * root.uiScale
                            Text { text: modelData; color: "#DCE2EE"; font.pixelSize: 14 * root.uiScale; Layout.fillWidth: true }
                            Text { text: "↗"; color: "#847BFF"; font.pixelSize: 17 * root.uiScale }
                        }
                        MouseArea {
                            id: hintArea
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: { root.runPrompt(modelData); root.close() }
                        }
                    }
                }
                Item { Layout.fillHeight: true }
            }
        }
    }
}