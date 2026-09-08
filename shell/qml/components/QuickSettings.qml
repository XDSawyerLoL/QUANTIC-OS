import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root
    property real uiScale: 1.0
    width: 380 * uiScale
    height: 338 * uiScale
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    onOpened: systemControls.refresh()

    background: Rectangle {
        radius: 22 * root.uiScale
        color: "#F0121925"
        border.color: "#334158"
    }

    component ControlTile: Rectangle {
        id: tile
        property string title: ""
        property string subtitle: ""
        property bool active: false
        signal triggered()
        Layout.fillWidth: true
        Layout.preferredHeight: 72 * root.uiScale
        radius: 17 * root.uiScale
        color: active ? "#26234D" : "#171E2A"
        border.color: active ? "#6359D6" : "#303B4E"
        Column {
            anchors.left: parent.left
            anchors.leftMargin: 14 * root.uiScale
            anchors.verticalCenter: parent.verticalCenter
            spacing: 3 * root.uiScale
            Text { text: tile.title; color: "#EEF2F8"; font.pixelSize: 13 * root.uiScale; font.weight: Font.Medium }
            Text { text: tile.subtitle; color: "#8F9BAE"; font.pixelSize: 11 * root.uiScale }
        }
        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: tile.triggered() }
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

            ControlTile {
                title: "Wi‑Fi"
                subtitle: systemControls.wifiEnabled ? "Activé" : "Désactivé"
                active: systemControls.wifiEnabled
                onTriggered: systemControls.setWifiEnabled(!systemControls.wifiEnabled)
            }
            ControlTile {
                title: "Bluetooth"
                subtitle: systemControls.bluetoothEnabled ? "Activé" : "Désactivé"
                active: systemControls.bluetoothEnabled
                onTriggered: systemControls.setBluetoothEnabled(!systemControls.bluetoothEnabled)
            }
            ControlTile {
                title: "Silencieux"
                subtitle: systemControls.muted ? "Actif" : "Désactivé"
                active: systemControls.muted
                onTriggered: systemControls.setMuted(!systemControls.muted)
            }
            ControlTile {
                title: "Énergie"
                subtitle: systemControls.powerProfile
                active: systemControls.powerProfile === "power-saver"
                onTriggered: systemControls.cyclePowerProfile()
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: "#263144" }

        RowLayout {
            Layout.fillWidth: true
            Text { text: "Volume"; color: "#B8C1D0"; font.pixelSize: 12 * root.uiScale; Layout.preferredWidth: 72 * root.uiScale }
            Slider {
                id: volume
                Layout.fillWidth: true
                from: 0; to: 100
                value: Math.min(100, systemControls.volumePercent)
                onPressedChanged: if (!pressed) systemControls.setVolumePercent(Math.round(value))
            }
            Text { text: Math.round(volume.value) + "%"; color: "#8F9BAE"; font.pixelSize: 11 * root.uiScale; Layout.preferredWidth: 36 * root.uiScale }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: systemControls.brightnessPercent >= 0
            Text { text: "Luminosité"; color: "#B8C1D0"; font.pixelSize: 12 * root.uiScale; Layout.preferredWidth: 72 * root.uiScale }
            Slider {
                id: brightness
                Layout.fillWidth: true
                from: 1; to: 100
                value: Math.max(1, systemControls.brightnessPercent)
                onPressedChanged: if (!pressed) systemControls.setBrightnessPercent(Math.round(value))
            }
            Text { text: Math.round(brightness.value) + "%"; color: "#8F9BAE"; font.pixelSize: 11 * root.uiScale; Layout.preferredWidth: 36 * root.uiScale }
        }

        Text {
            Layout.fillWidth: true
            text: systemControls.statusText
            color: "#7F8BA0"
            font.pixelSize: 10 * root.uiScale
            elide: Text.ElideRight
        }
    }
}
