import QtQuick
import QtQuick.Controls
Item {
    id: root
    property string title
    property string iconSource
    property bool selected: false
    signal activated()
    width: 96; height: 80
    Rectangle { anchors.fill: parent; radius: 18; color: mouse.containsMouse ? "#162338" : "transparent"; opacity: mouse.pressed ? 0.75 : 1; Behavior on color { ColorAnimation { duration: 130 } } }
    Column {
        anchors.centerIn: parent; spacing: 7
        Image { source: root.iconSource; width: 25; height: 25; fillMode: Image.PreserveAspectFit; anchors.horizontalCenter: parent.horizontalCenter; opacity: 0.96 }
        Label { text: root.title; color: root.selected ? "#F4F6FF" : "#C7D0E2"; font.pixelSize: 12; anchors.horizontalCenter: parent.horizontalCenter }
    }
    Rectangle { width: 24; height: 3; radius: 2; anchors.bottom: parent.bottom; anchors.bottomMargin: 2; anchors.horizontalCenter: parent.horizontalCenter; color: "#607CFF"; visible: root.selected }
    MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.activated() }
}
