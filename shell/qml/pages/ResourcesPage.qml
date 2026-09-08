import QtQuick
import QtQuick.Controls
import Quantic.Home

Item {
    id: root
    property real unit: Math.max(0.8, Math.min(width / 1920, height / 1080))

    Text {
        x: 54 * root.unit
        y: 44 * root.unit
        text: "Q-Resource Center"
        color: "white"
        font.pixelSize: 36 * root.unit
        font.weight: Font.Light
    }

    Text {
        x: 54 * root.unit
        y: 94 * root.unit
        text: "Mesures réelles et décisions explicables. Aucun gain n’est déclaré sans mesure."
        color: "#9EAAC0"
        font.pixelSize: 14 * root.unit
    }

    Row {
        x: 54 * root.unit
        y: 150 * root.unit
        spacing: 14 * root.unit

        MetricCard {
            label: "CPU"
            ratio: backend.cpu / 100
            value: Math.round(backend.cpu) + " %"
            history: backend.cpuHistory
            accent: "#5A7DFF"
        }
        MetricCard {
            label: "GPU"
            ratio: Math.max(0, backend.gpu) / 100
            value: backend.gpuText
            history: backend.gpuHistory
            accent: "#9867FF"
        }
        MetricCard {
            label: "RAM"
            ratio: backend.ramPercent / 100
            value: backend.ramPercent.toFixed(0) + " %"
            history: backend.ramHistory
            accent: "#5DD7E9"
        }
    }

    GlassPanel {
        x: 54 * root.unit
        y: 390 * root.unit
        width: 720 * root.unit
        height: 180 * root.unit

        Column {
            anchors.fill: parent
            anchors.margins: 22 * root.unit
            spacing: 9 * root.unit

            Text {
                text: "Décision actuelle"
                color: "white"
                font.pixelSize: 18 * root.unit
            }
            Text {
                text: "Mode : " + backend.workload
                color: "#778AFF"
                font.pixelSize: 15 * root.unit
            }
            Text {
                text: backend.activityDetail
                color: "#AAB6CA"
                width: parent.width
                wrapMode: Text.WordWrap
                font.pixelSize: 13 * root.unit
            }
            Button {
                text: "Analyser maintenant"
                onClicked: backend.optimize()
            }
        }
    }
}
