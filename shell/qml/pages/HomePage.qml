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
            text: "Q U A N T I C   H O M E"
            color: "#EEF2FA"
            font.pixelSize: 17 * root.unit
            font.letterSpacing: 4 * root.unit
        }

        Text {
            x: 0
            y: 68 * root.unit
            text: "Bonjour"
            color: "#FCFDFF"
            font.pixelSize: 39 * root.unit
            font.weight: Font.Light
        }

        Row {
            x: 0
            y: 130 * root.unit
            spacing: 10 * root.unit

            Rectangle {
                width: 11 * root.unit
                height: 11 * root.unit
                radius: width / 2
                color: "#42D990"
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: backend.healthText
                color: "#46D68D"
                font.pixelSize: 16 * root.unit
            }
        }

        Row {
            x: 0
            y: 183 * root.unit
            spacing: 12 * root.unit

            MetricCard {
                width: 176 * root.unit
                height: 196 * root.unit
                label: "CPU"
                ratio: backend.cpu / 100
                value: Math.round(backend.cpu) + " %"
                history: backend.cpuHistory
                accent: "#5A7DFF"
            }
            MetricCard {
                width: 176 * root.unit
                height: 196 * root.unit
                label: "GPU"
                ratio: Math.max(0, backend.gpu) / 100
                value: backend.gpuText
                history: backend.gpuHistory
                accent: "#8065FF"
            }
            MetricCard {
                width: 176 * root.unit
                height: 196 * root.unit
                label: "RAM"
                ratio: backend.ramPercent / 100
                value: backend.ramUsedGb.toFixed(1) + " / " + backend.ramTotalGb.toFixed(0) + " GB"
                history: backend.ramHistory
                accent: "#9767FF"
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
                        color: "#D6DEEF"
                        font.pixelSize: 15 * root.unit
                        font.weight: Font.DemiBold
                    }
                    Text {
                        text: backend.safeMode ? "Protégé ✓" : "Optimisé ✓"
                        color: "#47DB91"
                        font.pixelSize: 20 * root.unit
                    }
                    Text {
                        text: backend.safeMode
                              ? "Live USB\nDisques internes protégés"
                              : "Système stable\nSurveillance active"
                        color: "#AAB5CA"
                        font.pixelSize: 12 * root.unit
                        lineHeight: 1.35
                    }
                }
            }
        }

        GlassPanel {
            x: 0
            y: 405 * root.unit
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
                    color: "#142238"
                    border.color: "#566BFF"

                    Text {
                        anchors.centerIn: parent
                        text: "✓"
                        color: "#7286FF"
                        font.pixelSize: 31 * root.unit
                    }
                }

                Column {
                    width: 460 * root.unit
                    spacing: 7 * root.unit
                    anchors.verticalCenter: parent.verticalCenter

                    Text {
                        text: backend.activityTitle
                        color: "#F4F6FB"
                        font.pixelSize: 16 * root.unit
                        font.weight: Font.Medium
                    }
                    Text {
                        text: backend.activityDetail
                        color: "#A9B4C8"
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
            y: 562 * root.unit
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
                    color: "#18233A"

                    Text {
                        anchors.centerIn: parent
                        text: "◈"
                        color: "#8C68FF"
                        font.pixelSize: 22 * root.unit
                    }
                }

                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 3 * root.unit

                    Text {
                        text: "Mode détecté : " + backend.workload
                        color: "#E9EDF7"
                        font.pixelSize: 14 * root.unit
                    }
                    Text {
                        text: "Optimisations sûres actives"
                        color: "#97A5BC"
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
                            color: "#F5F7FC"
                            font.pixelSize: 17 * root.unit
                            font.weight: Font.DemiBold
                        }
                        Item {
                            width: Math.max(0, parent.width - 135 * root.unit)
                            height: 1
                        }
                        Text {
                            text: "Q"
                            color: "#6E70FF"
                            font.pixelSize: 25 * root.unit
                            font.weight: Font.Bold
                        }
                    }

                    Rectangle {
                        width: parent.width
                        height: 143 * root.unit
                        radius: 17 * root.unit
                        color: "#1D2738"
                        border.width: 1
                        border.color: "#3A465A"

                        Text {
                            anchors.fill: parent
                            anchors.margins: 16 * root.unit
                            text: backend.companionMessage
                            color: "#E8ECF5"
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
                            color: "#F5F7FC"
                            font.pixelSize: 16 * root.unit
                            font.weight: Font.DemiBold
                        }
                        Item {
                            width: Math.max(0, parent.width - 180 * root.unit)
                            height: 1
                        }
                        Text {
                            text: "Q-Resource Center"
                            color: "#7389FF"
                            font.pixelSize: 11 * root.unit
                        }
                    }

                    Text {
                        text: "Quantic mesure les ressources en temps réel."
                        color: "#9EAAC0"
                        font.pixelSize: 11.5 * root.unit
                    }
                    ResourceRow {
                        width: parent.width
                        label: "CPU"
                        value: Math.round(backend.cpu) + " %"
                        history: backend.cpuHistory
                        accent: "#6382FF"
                    }
                    ResourceRow {
                        width: parent.width
                        label: "GPU"
                        value: backend.gpuText
                        history: backend.gpuHistory
                        accent: "#9A68FF"
                    }
                    ResourceRow {
                        width: parent.width
                        label: "RAM"
                        value: backend.ramPercent.toFixed(0) + " %"
                        history: backend.ramHistory
                        accent: "#5BD8E8"
                    }
                }
            }
        }
    }
}
