import QtQuick
import QtQuick.Controls
import Quantic.Home

Item {
    id: root
    property real unit: Math.max(0.8, Math.min(width / 1920, height / 1080))

    Text {
        x: 54 * root.unit
        y: 44 * root.unit
        text: "Q-Lab"
        color: "white"
        font.pixelSize: 36 * root.unit
        font.weight: Font.Light
    }

    Text {
        x: 54 * root.unit
        y: 94 * root.unit
        text: "Expériences quantiques simulées localement. Les calculs restent classiques sur ce matériel."
        color: "#9EAAC0"
        font.pixelSize: 14 * root.unit
    }

    Row {
        x: 54 * root.unit
        y: 150 * root.unit
        spacing: 18 * root.unit

        Repeater {
            model: [
                ["État de Bell", "Prépare |Φ+⟩ et affiche 00/11.", "bell"],
                ["Bell / CHSH", "Borne classique 2 vs quantum ≈2,828.", "chsh"]
            ]

            GlassPanel {
                width: 390 * root.unit
                height: 220 * root.unit

                Column {
                    anchors.fill: parent
                    anchors.margins: 24 * root.unit
                    spacing: 14 * root.unit

                    Text {
                        text: modelData[0]
                        color: "white"
                        font.pixelSize: 21 * root.unit
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: modelData[1]
                        color: "#9EAAC0"
                        font.pixelSize: 13.5 * root.unit
                        width: parent.width
                        wrapMode: Text.WordWrap
                    }
                    Button {
                        text: "Exécuter"
                        onClicked: backend.runLab(modelData[2])
                    }
                }
            }
        }
    }

    GlassPanel {
        x: 54 * root.unit
        y: 395 * root.unit
        width: 798 * root.unit
        height: 230 * root.unit

        Text {
            anchors.fill: parent
            anchors.margins: 22 * root.unit
            text: backend.labOutput
            color: "#CBD7EB"
            font.family: "monospace"
            font.pixelSize: 13 * root.unit
            wrapMode: Text.WrapAnywhere
        }
    }
}
