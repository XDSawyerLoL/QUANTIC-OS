import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    property string currentPage: "Accueil"
    property real uiScale: 1.0
    signal navigate(string page)
    signal commandCenter()
    signal companion()

    width: Math.min(parent ? parent.width - 48 : 980, 980 * uiScale)
    height: 64 * uiScale
    radius: height / 2
    color: "#D9082135"
    border.color: "#38586A"
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 10 * root.uiScale
        anchors.rightMargin: 10 * root.uiScale
        spacing: 4 * root.uiScale

        ToolButton {
            id: qButton
            Layout.preferredWidth: 48 * root.uiScale
            Layout.preferredHeight: 48 * root.uiScale
            text: "Q"
            font.pixelSize: 22 * root.uiScale
            font.weight: Font.DemiBold
            palette.buttonText: "#D9FAFF"
            background: Rectangle {
                radius: width / 2
                color: qButton.hovered ? "#123F50" : "#0B3144"
                border.color: "#00D9FF"
            }
            onClicked: root.companion()
        }

        ToolButton {
            id: searchButton
            Layout.preferredWidth: 48 * root.uiScale
            Layout.preferredHeight: 48 * root.uiScale
            text: "⌕"
            font.pixelSize: 25 * root.uiScale
            palette.buttonText: "#E8FCFF"
            background: Rectangle { radius: width / 2; color: searchButton.hovered ? "#12384B" : "transparent" }
            onClicked: root.commandCenter()
        }

        Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 30 * root.uiScale; color: "#2B5264" }

        Repeater {
            model: [
                ["Accueil", "⌂"],
                ["Apps", "▦"],
                ["Fichiers", "▰"],
                ["Lab", "◇"]
            ]
            ToolButton {
                required property var modelData
                Layout.preferredWidth: 54 * root.uiScale
                Layout.preferredHeight: 48 * root.uiScale
                text: modelData[1]
                font.pixelSize: 20 * root.uiScale
                palette.buttonText: root.currentPage === modelData[0] ? "#FFFFFF" : "#A9C7D1"
                background: Rectangle {
                    radius: 16 * root.uiScale
                    color: parent.hovered ? "#12384B" : "transparent"
                    Rectangle {
                        visible: root.currentPage === modelData[0]
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 4
                        width: 18 * root.uiScale
                        height: 2
                        radius: 1
                        color: "#00D9FF"
                    }
                }
                onClicked: root.navigate(modelData[0])
                ToolTip.visible: hovered
                ToolTip.text: modelData[0]
            }
        }

        Item { Layout.fillWidth: true }

        Text {
            text: "● Quantic OS prêt"
            color: "#9FC7D1"
            font.pixelSize: 12 * root.uiScale
            Layout.rightMargin: 8 * root.uiScale
        }

        Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 30 * root.uiScale; color: "#2B5264" }

        Text { text: "⌁"; color: "#C8EAF0"; font.pixelSize: 18 * root.uiScale }
        Text { text: "◖"; color: "#C8EAF0"; font.pixelSize: 18 * root.uiScale }
        Text {
            id: clock
            color: "#F4FCFF"
            font.pixelSize: 14 * root.uiScale
            font.weight: Font.Medium
            text: Qt.formatDateTime(new Date(), "HH:mm")
        }
        Timer { interval: 1000; running: true; repeat: true; onTriggered: clock.text = Qt.formatDateTime(new Date(), "HH:mm") }
    }
}
