import QtQuick
import QtQuick.Controls
import Quantic.Home

Item {
    id: root
    property real unit: Math.max(0.8, Math.min(width / 1920, height / 1080))

    Text {
        x: 54 * root.unit
        y: 44 * root.unit
        text: "Compagnon"
        color: "white"
        font.pixelSize: 36 * root.unit
        font.weight: Font.Light
    }

    Text {
        x: 54 * root.unit
        y: 94 * root.unit
        text: "Local par défaut. Mémoire locale. Actions système soumises aux permissions Quantic."
        color: "#9EAAC0"
        font.pixelSize: 14 * root.unit
    }

    GlassPanel {
        x: 54 * root.unit
        y: 145 * root.unit
        width: Math.min(900 * root.unit, root.width - 108 * root.unit)
        height: 510 * root.unit

        Column {
            anchors.fill: parent
            anchors.margins: 26 * root.unit
            spacing: 16 * root.unit

            Row {
                width: parent.width
                spacing: 10 * root.unit

                Text {
                    text: "Q"
                    color: "#7B6DFF"
                    font.pixelSize: 28 * root.unit
                    font.weight: Font.Bold
                }
                Text {
                    text: backend.localAiStatus
                    color: "#B9C4D8"
                    font.pixelSize: 14 * root.unit
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Rectangle {
                width: parent.width
                height: 245 * root.unit
                radius: 18 * root.unit
                color: "#182233"
                border.color: "#34445D"

                Text {
                    anchors.fill: parent
                    anchors.margins: 20 * root.unit
                    text: backend.companionMessage
                    color: "#EDF1F8"
                    wrapMode: Text.WordWrap
                    font.pixelSize: 15 * root.unit
                    lineHeight: 1.35
                }
            }

            TextArea {
                id: input
                width: parent.width
                height: 95 * root.unit
                placeholderText: "Parler à Quantic…"
                wrapMode: TextEdit.Wrap
            }

            Row {
                spacing: 12 * root.unit

                Button {
                    text: backend.companionBusy ? "Réflexion…" : "Envoyer"
                    enabled: !backend.companionBusy && input.text.trim().length > 0
                    onClicked: {
                        backend.askCompanion(input.text)
                        input.clear()
                    }
                }
                Button {
                    text: "Analyser le système"
                    onClicked: backend.optimize()
                }
            }
        }
    }
}
