import QtQuick
import QtQuick.Effects
Rectangle {
    id: root
    property color panelColor: "#B5141B2A"
    property color edgeColor: "#52606F89"
    radius: 24
    color: panelColor
    border.width: 1
    border.color: edgeColor
    layer.enabled: true
    layer.effect: MultiEffect {
        shadowEnabled: true
        shadowColor: "#A0000000"
        shadowOpacity: 0.48
        shadowBlur: 0.55
        shadowVerticalOffset: 10
    }
    Rectangle { anchors.fill: parent; anchors.margins: 1; radius: parent.radius - 1; color: "transparent"; border.width: 1; border.color: "#182E4162" }
}
