import QtQuick
import QtQuick.Effects
Rectangle {
    id: root
    property color panelColor: "#B50A2235"
    property color edgeColor: "#663C7182"
    radius: 24
    color: panelColor
    border.width: 1
    border.color: edgeColor
    layer.enabled: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: "#A0000000"
        shadowOpacity: 0.42
        shadowBlur: 0.55
        shadowVerticalOffset: 10
    }
    Rectangle { anchors.fill: parent; anchors.margins: 1; radius: parent.radius - 1; color: "transparent"; border.width: 1; border.color: "#183D6B7D" }
}
