import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root
    property real uiScale: 1.0
    signal layoutChosen(string layoutId)
    width: 420 * uiScale
    height: 180 * uiScale
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
        Text { text: "Q‑Snap"; color: "#F3F6FB"; font.pixelSize: 18 * root.uiScale; font.weight: Font.DemiBold }
        Text { text: "Organiser l’espace de travail"; color: "#8F9BAE"; font.pixelSize: 11 * root.uiScale }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10 * root.uiScale
            Repeater {
                model: [["split","50 / 50"],["focus","65 / 35"],["triple","50 / 25 / 25"]]
                delegate: Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 78 * root.uiScale
                    radius: 16 * root.uiScale
                    color: mouse.containsMouse ? "#242A3A" : "#171E2A"
                    border.color: mouse.containsMouse ? "#655BDA" : "#303B4E"
                    Text { anchors.centerIn: parent; text: modelData[1]; color: "#DDE3EC"; font.pixelSize: 12 * root.uiScale }
                    MouseArea {
                        id: mouse
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: { root.layoutChosen(modelData[0]); root.close() }
                    }
                }
            }
        }
    }
}
