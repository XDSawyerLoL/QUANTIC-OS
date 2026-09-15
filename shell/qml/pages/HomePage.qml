import QtQuick
import QtQuick.Controls
import Quantic.Home

Item {
    id: root
    property real unit: Math.max(0.80, Math.min(width / 1920, height / 1080))
    signal navigate(string page)

    Item {
        id: stage
        width: Math.min(root.width - 72 * root.unit, 2500 * root.unit)
        height: root.height - 126 * root.unit
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 26 * root.unit

        Text {
            x: 0
            y: 0
            text: "Q U A N T I C   O S"
            color: "#EAFBFF"
            font.pixelSize: 17 * root.unit
            font.letterSpacing: 4 * root.unit
        }

        Text {
            x: 0
            y: 68 * root.unit
            text: "Bonjour"
            color: "#FCFEFF"
            font.pixelSize: 39 * root.unit
            font.weight: Font.Light
        }

        Text {
            x: 0
            y: 113 * root.unit
            text: "THE INTELLIGENCE LAYER"
            color: "#7FEAFF"
            font.pixelSize: 10.5 * root.unit
            font.letterSpacing: 3.2 * root.unit
        }

        Row {
            x: 0
            y: 150 * root.unit
            spacing: 10 * root.unit

            Rectangle {
                width: 11 * root.unit
                height: 11 * root.unit
                radius: width / 2
                color: "#14B8A6"
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: backend.healthText
                color: "#7DE7D9"
                font.pixelSize: 16 * root.unit
            }
        }

        Row {
            x: 0
            y: 198 * root.unit
            spacing: 12 * root.unit

            MetricCard {
                width: 176 * root.unit
                height: 196 * root.unit
                label: "CPU"
                ratio: backend.cpu / 100
                value: Math.round(backend.cpu) + " %"
                history: backend.cpuHistory
                accent: "#00D9FF"
            }
            MetricCard {
                width: 176 * root.unit
                height: 196 * root.unit
                label: "GPU"
                ratio: Math.max(0, backend.gpu) / 100
                value: backend.gpuText
                history: backend.gpuHistory
                accent: "#14B8A6"
            }
            MetricCard {
                width: 176 * root.unit
                height: 196 * root.unit
                label: "RAM"
                ratio: backend.ramPercent / 100
                value: backend.ramUsedGb.toFixed(1) + " / " + backend.ramTotalGb.toFixed(0) + " GB"
                history: backend.ramHistory
                accent: "#7FEAFF"
            }
            GlassPanel {
                width: 176 * root.unit
                height: 196 * root.unit

                Column {
                    anchors.fill: parent
                    anchors.margins: 20 * root.unit
                    spacing: 21 * root.unit

                    Text {
                        text: "Q-STATUS"
                        color: "#D9F4FA"
                        font.pixelSize: 15 * root.unit
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: backend.safeMode ? "Protégé ✓" : "Optimisé ✓"
                        color: "#68E1D1"
                        font.pixelSize: 20 * root.unit
                    }
                    Text {
                        text: backend.safeMode
                              ? "Live USB\nDisques internes protégés"
                              : "Système stable\nSurveillance active"
                        color: "#A6C1CB"
                        font.pixelSize: 12 * root.unit
                        lineHeight: 1.35
                    }
                }
            }
        }

        GlassPanel {
            x: 0
            y: 420 * root.unit
            width: 720 * root.unit
            height: 135 * root.unit

            Row {
                anchors.fill: parent
                anchors.margins: 22 * root.unit
                spacing: 22 * root.unit

                Rectangle {
                    width: 72 * root.unit
                    height: 72 * root.unit
                    radius: 18 * root.unit
                    color: "#0B3144"
                    border.color: "#00D9FF"

                    Text {
                        anchors.centerIn: parent
                        text: "✓"
                        color: "#7FEAFF"
                        font.pixelSize: 31 * root.unit
                    }
                }

                Column {
                    width: 460 * root.unit
                    spacing: 7 * root.unit
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        text: backend.activityTitle
                        color: "#F4FDFF"
                        font.pixelSize: 16 * root.unit
                        font.weight: Font.Medium
                    }
                    Text {
                        text: backend.activityDetail
                        color: "#A7C2CC"
                        font.pixelSize: 12.5 * root.unit
                        wrapMode: Text.WordWrap
                        width: parent.width
                        lineHeight: 1.25
                    }
                }

                Button {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Voir"
                    onClicked: root.navigate("Ressources")
                }
            }
        }

        GlassPanel {
            x: 0
            y: 577 * root.unit
            width: 340 * root.unit
            height: 80 * root.unit

            Row {
                anchors.fill: parent
                anchors.margins: 18 * root.unit
                spacing: 13 * root.unit

                Rectangle {
                    width: 42 * root.unit
                    height: 42 * root.unit
                    radius: 12 * root.unit
                    color: "#0B3144"

                    Text {
                        anchors.centerIn: parent
                        text: "◈"
                        color: "#00D9FF"
                        font.pixelSize: 22 * root.unit
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3 * root.unit

                    Text {
                        text: "Mode détecté : " + backend.workload
                        color: "#E9F8FB"
                        font.pixelSize: 14 * root.unit
                    }
                    Text {
                        text: "Optimisations sûres actives"
                        color: "#94B6C0"
                        font.pixelSize: 11.5 * root.unit
                    }
                }
            }
        }

        ParticleQ {
            width: 600 * root.unit
            height: width
            x: stage.width * 0.50 - width / 2
            y: 95 * root.unit
        }

        Column {
            width: 360 * root.unit
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: 42 * root.unit
            spacing: 16 * root.unit

            GlassPanel {
                width: parent.width
                height: 330 * root.unit

                Column {
                    anchors.fill: parent
                    anchors.margins: 22 * root.unit
                    spacing: 15 * root.unit

                    Row {
                        width: parent.width

                        Text {
                            text: "Compagnon"
                            color: "#F5FDFF"
                            font.pixelSize: 17 * root.unit
                            font.weight: Font.DemiBold
                        }
                        Item {
                            width: Math.max(0, parent.width - 135 * root.unit)
                            height: 1
                        }
                        Text {
                            text: "Q"
                            color: "#00D9FF"
                            font.pixelSize: 25 * root.unit
                            font.weight: Font.Bold
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 143 * root.unit
                        radius: 17 * root.unit
                        color: "#0B293B"
                        border.width: 1
                        border.color: "#31586A"

                        Text {
                            anchors.fill: parent
                            anchors.margins: 16 * root.unit
                            text: backend.companionMessage
                            color: "#E8F7FA"
                            wrapMode: Text.WordWrap
                            font.pixelSize: 13.5 * root.unit
                            lineHeight: 1.32
                        }
                    }

                    Button {
                        width: parent.width
                        height: 42 * root.unit
                        text: "Optimiser"
                        onClicked: backend.optimize()
                    }
                    Button {
                        width: parent.width
                        height: 38 * root.unit
                        text: "Ouvrir le compagnon"
                        onClicked: root.navigate("Compagnon")
                    }
                }
            }

            GlassPanel {
                width: parent.width
                height: 245 * root.unit

                Column {
                    anchors.fill: parent
                    anchors.margins: 20 * root.unit
                    spacing: 10 * root.unit

                    Row {
                        width: parent.width

                        Text {
                            text: "Ressources"
                            color: "#F5FDFF"
                            font.pixelSize: 16 * root.unit
                            font.weight: Font.DemiBold
                        }
                        Item {
                            width: Math.max(0, parent.width - 180 * root.unit)
                            height: 1
                        }
                        Text {
                            text: "Q-Resource Center"
                            color: "#00D9FF"
                            font.pixelSize: 11 * root.unit
                        }
                    }

                    Text {
                        text: "Quantic mesure les ressources en temps réel."
                        color: "#9DBAC4"
                        font.pixelSize: 11.5 * root.unit
                    }
                    ResourceRow {
                        width: parent.width
                        label: "CPU"
                        value: Math.round(backend.cpu) + " %"
                        history: backend.cpuHistory
                        accent: "#00D9FF"
                    }
                    ResourceRow {
                        width: parent.width
                        label: "GPU"
                        value: backend.gpuText
                        history: backend.gpuHistory
                        accent: "#14B8A6"
                    }
                    ResourceRow {
                        width: parent.width
                        label: "RAM"
                        value: backend.ramPercent.toFixed(0) + " %"
                        history: backend.ramHistory
                        accent: "#7FEAFF"
                    }
                }
            }
        }
    }
}
