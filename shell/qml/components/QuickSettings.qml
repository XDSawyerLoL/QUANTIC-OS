import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root
    property real uiScale: 1.0
    width: 360 * uiScale
    height: 300 * uiScale
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    background: Rectangle {
        radius: 22 * root.uiScale
        color: "#F0121925"
        border.color: "#334158"
    }
    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18 * root.uiScale
        spacing: 12 * root.uiScale
        RowLayout {
            Layout.fillWidth: true
            Text { text: "Réglages rapides"; color: "#F3F6FB"; font.pixelSize: 18 * root.uiScale; font.weight: Font.DemiBold }
            Item { Layout.fillWidth: true }
            Text { text: Qt.formatDateTime(new Date(), "HH:mm"); color: "#9CA8BA"; font.pixelSize: 13 * root.uiScale }
        }
        GridLayout {
            Layout.fillWidth: true
            columns: 2
            rowSpacing: 10 * root.uiScale
            columnSpacing: 10 * root.uiScale
            Repeater {
                model: [
                    ["Wi‑Fi", "Connecté", true],
                    ["Bluetooth", "Actif", true],
                    ["Silencieux", "Désactivé", false],
                    ["Économie", "Auto", false]
                ]
                delegate: Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 72 * root.uiScale
                    radius: 17 * root.uiScale
                    color: modelData[2] ? "#26234D" : "#171E2A"
                    border.color: modelData[2] ? "#6359D6" : "#303B4E"
                    Column {
                        anchors.left: parent.left; anchors.leftMargin: 14 * root.uiScale
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3 * root.uiScale
                        Text { text: modelData[0]; color: "#EEF2F8"; font.pixelSize: 13 * root.uiScale; font.weight: Font.Medium }
                        Text { text: modelData[1]; color: "#8F9BAE"; font.pixelSize: 11 * root.uiScale }
                    }
                }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: "#263144" }
        RowLayout {
            Layout.fillWidth: true
            Text { text: "Volume"; color: "#B8C1D0"; font.pixelSize: 12 * root.uiScale }
            Slider { Layout.fillWidth: true; from: 0; to: 100; value: 62 }
        }
        RowLayout {
            Layout.fillWidth: true
            Text { text: "Luminosité"; color: "#B8C1D0"; font.pixelSize: 12 * root.uiScale }
            Slider { Layout.fillWidth: true; from: 0; to: 100; value: 74 }
        }
    }
}
