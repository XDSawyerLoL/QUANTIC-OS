import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root
    property real uiScale: 1.0
    width: 400 * uiScale
    height: 360 * uiScale
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
            Text { text: "Notifications"; color: "#F3F6FB"; font.pixelSize: 18 * root.uiScale; font.weight: Font.DemiBold }
            Item { Layout.fillWidth: true }
            Text { text: "Tout effacer"; color: "#9188FF"; font.pixelSize: 11 * root.uiScale }
        }
        Repeater {
            model: [
                ["Quantic", "Aucun problème système détecté.", "maintenant"],
                ["Mission · Quantic OS", "3 éléments prêts à reprendre.", "il y a 4 min"],
                ["Sécurité", "Les actions sensibles restent sous validation.", "il y a 12 min"]
            ]
            delegate: Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 78 * root.uiScale
                radius: 17 * root.uiScale
                color: "#151D29"
                border.color: "#2D394D"
                Column {
                    anchors.left: parent.left; anchors.right: parent.right
                    anchors.leftMargin: 14 * root.uiScale; anchors.rightMargin: 14 * root.uiScale
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 4 * root.uiScale
                    Row {
                        spacing: 8 * root.uiScale
                        Text { text: modelData[0]; color: "#F0F3F8"; font.pixelSize: 13 * root.uiScale; font.weight: Font.Medium }
                        Text { text: modelData[2]; color: "#748197"; font.pixelSize: 10 * root.uiScale }
                    }
                    Text { width: parent.width; text: modelData[1]; color: "#9DA9BB"; font.pixelSize: 11 * root.uiScale; wrapMode: Text.WordWrap }
                }
            }
        }
        Item { Layout.fillHeight: true }
    }
}
