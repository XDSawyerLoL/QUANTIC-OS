import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root
    property real uiScale: 1.0
    width: 520 * uiScale
    height: 390 * uiScale
    modal: true
    focus: true
    closePolicy: Popup.NoAutoClose
    background: Rectangle {
        radius: 26 * root.uiScale
        color: "#F3131924"
        border.color: "#4A5770"
    }
    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 22 * root.uiScale
        spacing: 14 * root.uiScale
        RowLayout {
            Layout.fillWidth: true
            Rectangle { width: 38 * root.uiScale; height: width; radius: width / 2; color: "#28214A"; Text { anchors.centerIn: parent; text: "Q"; color: "#A79EFF"; font.bold: true } }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text { text: "Autorisation requise"; color: "#F4F6FB"; font.pixelSize: 19 * root.uiScale; font.weight: Font.DemiBold }
                Text { text: "Quantic s’est arrêté avant une action sensible."; color: "#98A4B7"; font.pixelSize: 11 * root.uiScale }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 184 * root.uiScale
            radius: 18 * root.uiScale
            color: "#151D29"
            border.color: "#2E3A4D"
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 15 * root.uiScale
                spacing: 8 * root.uiScale
                Text { text: authorizationBridge.request.tool || "Action système"; color: "#EEF2F8"; font.pixelSize: 15 * root.uiScale; font.weight: Font.Medium }
                RowLayout {
                    Text { text: "Risque  " + (authorizationBridge.request.risk || "inconnu"); color: "#C5A7FF"; font.pixelSize: 11 * root.uiScale }
                    Text { text: authorizationBridge.request.reversible ? "Réversible" : "Non garantie réversible"; color: authorizationBridge.request.reversible ? "#8FD7B3" : "#E6B17A"; font.pixelSize: 11 * root.uiScale }
                    Item { Layout.fillWidth: true }
                }
                Text { text: "Capacité : " + (authorizationBridge.request.capability || "système"); color: "#95A1B4"; font.pixelSize: 11 * root.uiScale }
                Rectangle { Layout.fillWidth: true; height: 1; color: "#273346" }
                Text {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    text: JSON.stringify(authorizationBridge.request.arguments || {}, null, 2)
                    color: "#BAC3D2"
                    font.family: "monospace"
                    font.pixelSize: 10 * root.uiScale
                    wrapMode: Text.WrapAnywhere
                    elide: Text.ElideRight
                }
            }
        }
        Text { Layout.fillWidth: true; text: authorizationBridge.status; color: "#8E9AAF"; font.pixelSize: 11 * root.uiScale; horizontalAlignment: Text.AlignHCenter }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10 * root.uiScale
            Button {
                Layout.fillWidth: true
                text: "Refuser"
                enabled: !authorizationBridge.busy
                onClicked: authorizationBridge.reject()
            }
            Button {
                Layout.fillWidth: true
                text: "Voir les changements"
                enabled: !authorizationBridge.busy
                onClicked: details.opened = !details.opened
            }
            Button {
                Layout.fillWidth: true
                text: authorizationBridge.busy ? "Traitement…" : "Autoriser"
                enabled: !authorizationBridge.busy
                onClicked: authorizationBridge.approve()
            }
        }
        Item { id: details; property bool opened: false }
        Text {
            visible: details.opened
            Layout.fillWidth: true
            text: "Simulation : " + JSON.stringify(authorizationBridge.request.simulation || {})
            color: "#8996AA"
            font.pixelSize: 10 * root.uiScale
            wrapMode: Text.WordWrap
        }
    }
}
