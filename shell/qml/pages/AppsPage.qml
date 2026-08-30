import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quantic.Home

Item {
    id: root
    property real unit: Math.max(0.8, Math.min(width / 1920, height / 1080))

    Text {
        x: 54 * root.unit
        y: 44 * root.unit
        text: "Applications"
        color: "white"
        font.pixelSize: 36 * root.unit
        font.weight: Font.Light
    }

    Text {
        x: 54 * root.unit
        y: 94 * root.unit
        text: "Linux natif, Windows via Q-Bridge. Quantic choisit la couche adaptée."
        color: "#9EAAC0"
        font.pixelSize: 15 * root.unit
    }

    Grid {
        x: 54 * root.unit
        y: 150 * root.unit
        columns: 3
        spacing: 18 * root.unit

        Repeater {
            model: [
                ["Logiciels", "Applications Fedora et Flatpak", "Découvrir", "AppsNative"],
                ["Q-Bridge", "Applications Windows avec Wine/Proton", "Ouvrir", "Bridge"],
                ["Fichiers", "Espaces autorisés de la clé", "Ouvrir", "Fichiers"],
                ["Système", "Écrans, son, réseau et périphériques", "Configurer", "Paramètres"],
                ["Terminal", "Diagnostics avancés", "Ouvrir", "Terminal"],
                ["Q-Lab", "Bell, CHSH et simulations", "Explorer", "Lab"]
            ]

            GlassPanel {
                width: 330 * root.unit
                height: 170 * root.unit

                Column {
                    anchors.fill: parent
                    anchors.margins: 22 * root.unit
                    spacing: 11 * root.unit

                    Text {
                        text: modelData[0]
                        color: "white"
                        font.pixelSize: 19 * root.unit
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: modelData[1]
                        width: parent.width
                        wrapMode: Text.WordWrap
                        color: "#9EAAC0"
                        font.pixelSize: 13 * root.unit
                    }
                    Button {
                        text: modelData[2]
                        onClicked: backend.openDestination(modelData[3])
                    }
                }
            }
        }
    }
}
