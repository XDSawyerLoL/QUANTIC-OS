import QtQuick
import QtQuick.Controls
import Quantic.Home

Item {
    id: root
    property real unit: Math.max(0.8, Math.min(width / 1920, height / 1080))

    Text {
        x: 54 * root.unit
        y: 44 * root.unit
        text: "Paramètres Quantic"
        color: "white"
        font.pixelSize: 36 * root.unit
        font.weight: Font.Light
    }

    Text {
        x: 54 * root.unit
        y: 94 * root.unit
        text: "Quantic simplifie le quotidien ; Plasma conserve les réglages matériels avancés."
        color: "#9EAAC0"
        font.pixelSize: 14 * root.unit
    }

    Column {
        x: 54 * root.unit
        y: 150 * root.unit
        spacing: 16 * root.unit

        GlassPanel {
            width: 720 * root.unit
            height: 120 * root.unit

            Row {
                anchors.fill: parent
                anchors.margins: 22 * root.unit
                spacing: 30 * root.unit

                Column {
                    width: 470 * root.unit
                    spacing: 5 * root.unit

                    Text {
                        text: "Mode Live USB protégé"
                        color: "white"
                        font.pixelSize: 18 * root.unit
                    }
                    Text {
                        text: backend.safeMode ? "Actif — disques internes protégés" : "Inactif"
                        color: backend.safeMode ? "#47DB91" : "#F6B45B"
                        font.pixelSize: 13 * root.unit
                    }
                }

                Text {
                    text: backend.safeMode ? "ACTIF" : "INACTIF"
                    color: backend.safeMode ? "#47DB91" : "#F6B45B"
                    font.pixelSize: 16 * root.unit
                    font.weight: Font.Bold
                }
            }
        }

        GlassPanel {
            width: 720 * root.unit
            height: 150 * root.unit

            Column {
                anchors.fill: parent
                anchors.margins: 22 * root.unit
                spacing: 10 * root.unit

                Text {
                    text: "Matériel"
                    color: "white"
                    font.pixelSize: 18 * root.unit
                }
                Text {
                    text: "Réseau : " + backend.networkText
                          + "    •    Audio : " + backend.volumeText
                          + "    •    CPU : " + backend.cpuTempText
                    color: "#AAB6CA"
                    font.pixelSize: 13 * root.unit
                    wrapMode: Text.WordWrap
                    width: parent.width
                }
                Button {
                    text: "Ouvrir les paramètres système"
                    onClicked: backend.openDestination("Paramètres")
                }
            }
        }
    }
}
