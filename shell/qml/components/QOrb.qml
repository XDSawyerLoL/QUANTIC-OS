import QtQuick
import QtQuick.Controls

Item {
    id: root
    property real uiScale: 1.0
    property string state: "prêt"
    property bool busy: false
    signal activated()
    signal holdVoice()
    width: 86 * uiScale
    height: 86 * uiScale

    Rectangle {
        id: halo
        anchors.centerIn: parent
        width: 82 * root.uiScale
        height: width
        radius: width / 2
        color: "transparent"
        border.width: 2 * root.uiScale
        border.color: root.state === "écoute" ? "#7FEAFF" : root.state === "parle" ? "#14B8A6" : root.busy ? "#00D9FF" : "#416677"
        opacity: root.state === "prêt" ? 0.58 : 0.98
        scale: 1.0
        SequentialAnimation on scale {
            running: root.busy || root.state !== "prêt"
            loops: Animation.Infinite
            NumberAnimation { to: 1.09; duration: 850; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1.0; duration: 850; easing.type: Easing.InOutSine }
        }
    }
    Rectangle {
        anchors.centerIn: parent
        width: 64 * root.uiScale
        height: width
        radius: width / 2
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#0B5262" }
            GradientStop { position: 0.55; color: "#0A3046" }
            GradientStop { position: 1.0; color: "#071827" }
        }
        border.color: "#00D9FF"
        Text {
            anchors.centerIn: parent
            text: "Q"
            color: "#F3FDFF"
            font.pixelSize: 25 * root.uiScale
            font.weight: Font.DemiBold
        }
    }
    MouseArea {
        id: hit
        anchors.fill: parent
        pressAndHoldInterval: 500
        onClicked: root.activated()
        onPressAndHold: root.holdVoice()
    }
    ToolTip.visible: hit.containsMouse
    ToolTip.text: root.state === "écoute" ? "Quantic écoute" : root.state === "parle" ? "Quantic parle" : "Cliquer pour ouvrir · maintenir pour parler"
}
