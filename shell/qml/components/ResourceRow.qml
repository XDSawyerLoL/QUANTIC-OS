import QtQuick
import QtQuick.Controls
Row {
    id: root
    property string label
    property string value
    property var history: []
    property color accent: "#627DFF"
    width: parent ? parent.width : 320; height: 44; spacing: 10
    Label { width: 52; text: root.label; color: "#D9E0EF"; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
    Label { width: 72; text: root.value; color: root.accent; font.pixelSize: 14; anchors.verticalCenter: parent.verticalCenter }
    Sparkline { width: Math.max(80, root.width-150); height: 28; values: root.history; lineColor: root.accent; anchors.verticalCenter: parent.verticalCenter }
}
