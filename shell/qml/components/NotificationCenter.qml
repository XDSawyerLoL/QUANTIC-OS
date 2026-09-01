import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root
    property real uiScale: 1.0
    width: 420 * uiScale
    height: 420 * uiScale
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    function ageLabel(ts) {
        var delta = Math.max(0, Math.floor(Date.now() / 1000 - ts))
        if (delta < 45) return "maintenant"
        if (delta < 3600) return "il y a " + Math.floor(delta / 60) + " min"
        if (delta < 86400) return "il y a " + Math.floor(delta / 3600) + " h"
        return "il y a " + Math.floor(delta / 86400) + " j"
    }

    onOpened: notificationBridge.refresh()

    background: Rectangle {
        radius: 22 * root.uiScale
        color: "#F0121925"
        border.color: "#334158"
    }

    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18 * root.uiScale
        spacing: 12 * root.uiScale

        RowLayout {
            Layout.fillWidth: true
            Text {
                text: notificationBridge.count > 0 ? "Notifications · " + notificationBridge.count : "Notifications"
                color: "#F3F6FB"
                font.pixelSize: 18 * root.uiScale
                font.weight: Font.DemiBold
            }
            Item { Layout.fillWidth: true }
            Text {
                text: "Tout effacer"
                color: notificationBridge.count > 0 ? "#9188FF" : "#596579"
                font.pixelSize: 11 * root.uiScale
                MouseArea {
                    anchors.fill: parent
                    enabled: notificationBridge.count > 0
                    cursorShape: Qt.PointingHandCursor
                    onClicked: notificationBridge.clearAll()
                }
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: "#263144" }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            visible: notificationBridge.count > 0

            ColumnLayout {
                width: parent.width
                spacing: 9 * root.uiScale
                Repeater {
                    model: notificationBridge.items
                    delegate: Rectangle {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(78 * root.uiScale, body.implicitHeight + 34 * root.uiScale)
                        radius: 17 * root.uiScale
                        color: "#151D29"
                        border.color: modelData.severity === "critical" ? "#7D3D54" : modelData.severity === "warning" ? "#67583B" : modelData.severity === "success" ? "#365B50" : "#2D394D"

                        Rectangle {
                            width: 4 * root.uiScale
                            height: parent.height - 24 * root.uiScale
                            anchors.left: parent.left
                            anchors.leftMargin: 8 * root.uiScale
                            anchors.verticalCenter: parent.verticalCenter
                            radius: 2 * root.uiScale
                            color: modelData.severity === "critical" ? "#FF728E" : modelData.severity === "warning" ? "#E6B864" : modelData.severity === "success" ? "#6FD6AD" : "#8177FF"
                        }

                        Column {
                            id: body
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.leftMargin: 20 * root.uiScale
                            anchors.rightMargin: 14 * root.uiScale
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 5 * root.uiScale
                            Row {
                                width: parent.width
                                spacing: 8 * root.uiScale
                                Text {
                                    text: modelData.title
                                    color: "#F0F3F8"
                                    font.pixelSize: 13 * root.uiScale
                                    font.weight: Font.Medium
                                }
                                Text {
                                    text: root.ageLabel(modelData.ts)
                                    color: "#748197"
                                    font.pixelSize: 10 * root.uiScale
                                }
                            }
                            Text {
                                width: parent.width
                                text: modelData.message
                                color: "#9DA9BB"
                                font.pixelSize: 11 * root.uiScale
                                wrapMode: Text.WordWrap
                            }
                            Text {
                                width: parent.width
                                text: modelData.topic
                                visible: text.length > 0
                                color: "#66758B"
                                font.pixelSize: 9 * root.uiScale
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: notificationBridge.count === 0
            Item { Layout.fillHeight: true }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "✓"
                color: "#6FD6AD"
                font.pixelSize: 28 * root.uiScale
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: "Rien ne demande ton attention"
                color: "#DCE3EE"
                font.pixelSize: 13 * root.uiScale
                font.weight: Font.Medium
            }
            Text {
                Layout.alignment: Qt.AlignHCenter
                text: notificationBridge.status
                color: "#79869A"
                font.pixelSize: 10 * root.uiScale
            }
            Item { Layout.fillHeight: true }
        }
    }
}
