import QtQuick
import QtQuick.Controls
import Quantic.Home

Item {
    id: root
    property real unit: Math.max(0.8, Math.min(width / 1920, height / 1080))

    Text {
        x: 54 * root.unit
        y: 44 * root.unit
        text: "Fichiers"
        color: "white"
        font.pixelSize: 36 * root.unit
        font.weight: Font.Light
    }

    Text {
        x: 54 * root.unit
        y: 94 * root.unit
        text: backend.safeMode ? "Live USB : les disques internes restent protégés." : "Accès aux espaces autorisés."
        color: backend.safeMode ? "#47DB91" : "#9EAAC0"
        font.pixelSize: 15 * root.unit
    }

    GlassPanel {
        x: 54 * root.unit
        y: 150 * root.unit
        width: 640 * root.unit
        height: 250 * root.unit

        Column {
            anchors.fill: parent
            anchors.margins: 26 * root.unit
            spacing: 17 * root.unit

            Text {
                text: "Stockage Quantic"
                color: "white"
                font.pixelSize: 20 * root.unit
            }
            Text {
                text: "Espace disponible : " + backend.diskFreeText
                color: "#B4C0D4"
                font.pixelSize: 15 * root.unit
            }
            Text {
                text: backend.safeMode
                      ? "Les supports internes sont présentés en lecture seule / masqués dans la session Live."
                      : "Protection Live inactive."
                color: "#91A0B8"
                font.pixelSize: 13 * root.unit
                width: parent.width
                wrapMode: Text.WordWrap
            }
            Button {
                text: "Ouvrir Dolphin"
                onClicked: backend.openDestination("Fichiers")
            }
        }
    }
}
