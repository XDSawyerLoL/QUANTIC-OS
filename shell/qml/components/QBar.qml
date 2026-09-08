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
    color: "#D9141B29"
    border.color: "#39445B"
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
            palette.buttonText: "#B7AEFF"
            background: Rectangle {
                radius: width / 2
                color: qButton.hovered ? "#2B2D52" : "#20233C"
                border.color: "#6E63D9"
            }
            onClicked: root.companion()
        }

        ToolButton {
            id: searchButton
            Layout.preferredWidth: 48 * root.uiScale
            Layout.preferredHeight: 48 * root.uiScale
            text: "⌕"
            font.pixelSize: 25 * root.uiScale
            palette.buttonText: "#E8ECF6"
            background: Rectangle { radius: width / 2; color: searchButton.hovered ? "#263044" : "transparent" }
            onClicked: root.commandCenter()
        }

        Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 30 * root.uiScale; color: "#344055" }

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
                palette.buttonText: root.currentPage === modelData[0] ? "#FFFFFF" : "#AAB4C8"
                background: Rectangle {
                    radius: 16 * root.uiScale
                    color: parent.hovered ? "#243049" : "transparent"
                    Rectangle {
                        visible: root.currentPage === modelData[0]
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 4
                        width: 18 * root.uiScale
                        height: 2
                        radius: 1
                        color: "#8177FF"
                    }
                }
                onClicked: root.navigate(modelData[0])
                ToolTip.visible: hovered
                ToolTip.text: modelData[0]
            }
        }

        Item { Layout.fillWidth: true }

        Text {
            text: "● Quantic prêt"
            color: "#9DA8BB"
            font.pixelSize: 12 * root.uiScale
            Layout.rightMargin: 8 * root.uiScale
        }

        Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 30 * root.uiScale; color: "#344055" }

        Text { text: "⌁"; color: "#C8D1E1"; font.pixelSize: 18 * root.uiScale }
        Text { text: "◖"; color: "#C8D1E1"; font.pixelSize: 18 * root.uiScale }
        Text {
            id: clock
            color: "#F4F6FA"
            font.pixelSize: 14 * root.uiScale
            font.weight: Font.Medium
            text: Qt.formatDateTime(new Date(), "HH:mm")
        }
        Timer { interval: 1000; running: true; repeat: true; onTriggered: clock.text = Qt.formatDateTime(new Date(), "HH:mm") }
    }
}