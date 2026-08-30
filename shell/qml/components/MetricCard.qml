import QtQuick
import QtQuick.Controls
GlassPanel {
    id: root
    property string label: "CPU"
    property string value: "0 %"
    property real ratio: 0
    property var history: []
    property color accent: "#627DFF"
    implicitWidth: 188; implicitHeight: 206
    Column {
        anchors.fill: parent; anchors.margins: 20; spacing: 9
        Row {
            width: parent.width; spacing: 9
            Rectangle { width: 24; height: 24; radius: 7; color: "#182439"; border.width: 1; border.color: "#3B4A63"
                Text { anchors.centerIn: parent; text: root.label === "RAM" ? "▥" : root.label === "GPU" ? "◫" : "▦"; color: "#D6DDF0"; font.pixelSize: 13 }
            }
            Label { text: root.label; color: "#DCE3F2"; font.pixelSize: 15; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
        }
        Item {
            width: 110; height: 110; anchors.horizontalCenter: parent.horizontalCenter
            Canvas {
                id: gauge; anchors.fill: parent
                onPaint: {
                    const c=getContext("2d"); c.reset(); c.lineWidth=9; c.lineCap="round";
                    c.strokeStyle="#293344"; c.beginPath(); c.arc(width/2,height/2,41,-Math.PI*0.82,Math.PI*0.82); c.stroke();
                    const g=c.createLinearGradient(12,12,width-12,height-12); g.addColorStop(0,"#4A78FF"); g.addColorStop(1,root.accent);
                    c.strokeStyle=g; c.shadowColor=root.accent; c.shadowBlur=8; c.beginPath(); c.arc(width/2,height/2,41,-Math.PI*0.82,-Math.PI*0.82+Math.PI*1.64*Math.max(0,Math.min(1,root.ratio))); c.stroke();
                }
            }
            Connections { target: root; function onRatioChanged(){ gauge.requestPaint() } }
            Label { anchors.centerIn: parent; text: root.value; color: "#F6F8FD"; font.pixelSize: root.label === "RAM" ? 16 : 23; font.weight: Font.Medium }
        }
        Sparkline { width: parent.width; height: 24; values: root.history; lineColor: root.accent }
    }
}
