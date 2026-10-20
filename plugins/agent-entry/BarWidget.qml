// Modified 2026-10-19: language-neutral bar label. Apache-2.0; see ORIGIN.md.
import QtQuick
import Quickshell

Item {
    id: root
    property QtObject bar: null
    property string moduleName: "anolisa.agent-entry"
    property var settings: ({})
    readonly property bool vertical: bar ? bar.vertical : false
    implicitWidth: vertical ? 28 : 65
    implicitHeight: 28

    Rectangle {
        anchors.fill: parent
        radius: 7
        color: hover.containsMouse ? "#344347" : "transparent"
        border.color: hover.containsMouse ? "#617778" : "transparent"
        Text {
            anchors.centerIn: parent
            text: root.vertical ? "A" : "◈ Agent"
            color: "#d0dad7"
            font.pixelSize: 12
            font.bold: true
        }
        MouseArea {
            id: hover
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: Quickshell.execDetached(["omarchy-shell", "shell", "toggle", root.moduleName, "{}"])
        }
    }
}
