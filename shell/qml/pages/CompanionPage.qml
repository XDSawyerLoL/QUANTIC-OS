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
        text: "Compagnon"
        color: "white"
        font.pixelSize: 36 * root.unit
        font.weight: Font.Light
    }

    Text {
        x: 54 * root.unit
        y: 94 * root.unit
        text: "Local par défaut. Écoute uniquement à la demande. Actions système soumises aux permissions Quantic."
        color: "#9EAAC0"
        font.pixelSize: 14 * root.unit
    }

    GlassPanel {
        x: 54 * root.unit
        y: 145 * root.unit
        width: Math.min(980 * root.unit, root.width - 108 * root.unit)
        height: 540 * root.unit

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 26 * root.unit
            spacing: 16 * root.unit

            RowLayout {
                Layout.fillWidth: true
                QOrb {
                    uiScale: root.unit
                    state: companionBridge.state
                    busy: backend.companionBusy
                    onActivated: input.forceActiveFocus()
                    onHoldVoice: companionBridge.listenOnce()
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: backend.localAiStatus; color: "#D8E0ED"; font.pixelSize: 14 * root.unit }
                    Text { text: companionBridge.voiceStatus; color: "#8F9CB1"; font.pixelSize: 12 * root.unit }
                    Text { text: companionBridge.listening ? "Je t’écoute…" : companionBridge.speaking ? "Je réponds…" : "Prêt"; color: "#9C92FF"; font.pixelSize: 12 * root.unit }
                }
                Button {
                    text: companionBridge.listening ? "Écoute…" : "Micro"
                    enabled: !companionBridge.listening
                    onClicked: companionBridge.listenOnce()
                }
                Button {
                    text: companionBridge.speaking ? "Stop" : "Lire"
                    onClicked: companionBridge.speaking ? companionBridge.stopSpeaking() : companionBridge.speak(backend.companionMessage)
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 250 * root.unit
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
                Layout.fillWidth: true
                Layout.preferredHeight: 92 * root.unit
                placeholderText: companionBridge.lastTranscript.length > 0 ? companionBridge.lastTranscript : "Parler à Quantic…"
                wrapMode: TextEdit.Wrap
            }

            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: backend.companionBusy ? "Réflexion…" : "Envoyer"
                    enabled: !backend.companionBusy && input.text.trim().length > 0
                    onClicked: { backend.askCompanion(input.text); input.clear() }
                }
                Button { text: "Analyser le système"; onClicked: backend.optimize() }
                Item { Layout.fillWidth: true }
                Text { text: "Maintiens le Q-Orb pour parler"; color: "#76849A"; font.pixelSize: 11 * root.unit }
            }
        }
    }
}
