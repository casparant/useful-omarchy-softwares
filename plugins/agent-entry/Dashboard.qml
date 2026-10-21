// Modified 2026-10-19: persistent language and localized async feedback. Apache-2.0; see ORIGIN.md.
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "I18n.js" as I18n

Item {
    id: root
    property var shell: null
    property var manifest: null
    readonly property bool opened: popup.visible || details.visible || window.visible
    readonly property string helper: decodeURIComponent(Qt.resolvedUrl("agent_entry.py").toString().replace(/^file:\/\//, ""))
    property string statusError: ""
    property string actionError: ""

    function open(payloadJson) {
        var payload = ({})
        try { payload = typeof payloadJson === "string" ? JSON.parse(payloadJson || "{}") : (payloadJson || ({})) } catch (e) {}
        root.close()
        if (payload && payload.view === "details") details.visible = true
        else popup.visible = true
        refresh()
    }
    function close() { popup.visible = false; details.visible = false; window.visible = false }
    function refresh() {
        if (statusProcess.running || actionProcess.running) return
        statusError = ""
        statusProcess.command = ["python3", helper, "status"]
        statusProcess.running = true
    }
    function act(args) {
        if (actionProcess.running || statusProcess.running) return
        actionError = ""
        content.message = ""
        actionProcess.command = ["python3", helper].concat(args)
        actionProcess.running = true
    }

    Process {
        id: statusProcess
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    if (result.language) content.language = result.language
                    if (result.error) { root.runtime = {state: "unavailable", sessions: []}; content.aw = { state: "query_failed" }; content.message = result.error }
                    else {
                        content.agents = result.agents
                        content.aw = result.aw
                        root.runtime = result.runtime || ({state: "unavailable", sessions: []})
                        content.project = result.project
                        content.configPath = result.config
                    }
                } catch (e) { root.runtime = {state: "unavailable", sessions: []}; content.aw = { state: "query_failed" }; content.message = I18n.text(content.language, "status_error") + String(e) }
            }
        }
        stderr: StdioCollector { onStreamFinished: root.statusError = text }
        onExited: function(code, status) {
            if (code !== 0) { root.runtime = {state: "unavailable", sessions: []}; content.aw = { state: "query_failed" }; content.message = root.statusError || I18n.text(content.language, "status_error") }
        }
    }
    Process {
        id: actionProcess
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    if (result.language) content.language = result.language
                    content.message = result.error || result.message || I18n.text(content.language, "done")
                    if (result.project) content.project = result.project
                } catch (e) { content.message = I18n.text(content.language, "action_error") + String(e) }
            }
        }
        stderr: StdioCollector { onStreamFinished: root.actionError = text }
        onExited: function(code, status) {
            if (code === 0 && ["launch", "return-session"].includes(actionProcess.command[2])) {
                if (window.visible) root.close()
                else if (details.visible) { details.visible = false; popup.visible = true }
            }
            if (code !== 0 && root.actionError) content.message = root.actionError
            refreshTimer.restart()
        }
    }
    Timer { interval: 5000; repeat: true; running: root.opened; onTriggered: root.refresh() }
    Timer { id: refreshTimer; interval: 200; onTriggered: root.refresh() }
    property var runtime: ({state: "unavailable", sessions: []})

    PanelWindow {
        id: popup
        visible: false
        anchors { top: true; right: true }
        margins { top: 44; right: 12 }
        implicitWidth: Math.min(460, (screen ? screen.width : 480) - 24)
        implicitHeight: Math.min(820, (screen ? screen.height : 900) - 80)
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "anolisa-control-plane"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
        ControlContent {
            anchors.fill: parent
            aw: content.aw; agents: content.agents; project: content.project
            runtime: root.runtime
            language: content.language; message: content.message
            busy: statusProcess.running || actionProcess.running
            onActionRequested: function(args) { root.act(args) }
            onRefreshRequested: root.refresh()
            onCloseRequested: popup.visible = false
            onDetailsRequested: { popup.visible = false; details.visible = true }
        }
    }
    PanelWindow {
        id: details
        visible: false
        implicitWidth: Math.min(1000, (screen ? screen.width : 1080) - 64)
        implicitHeight: Math.min(920, (screen ? screen.height : 1000) - 80)
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "anolisa-workbench"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
        ControlContent {
            anchors.fill: parent
            compact: false
            aw: content.aw; agents: content.agents; project: content.project
            runtime: root.runtime
            language: content.language; message: content.message
            busy: statusProcess.running || actionProcess.running
            onActionRequested: function(args) { root.act(args) }
            onRefreshRequested: root.refresh()
            onCloseRequested: { details.visible = false; popup.visible = true }
            onCatalogRequested: { details.visible = false; window.visible = true }
        }
    }
    FloatingWindow {
        id: window
        title: I18n.text(content.language, "window_title")
        visible: false
        implicitWidth: 1160
        implicitHeight: 740
        minimumSize: Qt.size(800, 560)
        color: "#111827"
        DashboardContent {
            id: content
            anchors.fill: parent
            busy: statusProcess.running || actionProcess.running
            onActionRequested: function(args) { root.act(args) }
            onRefreshRequested: root.refresh()
            onCloseRequested: root.close()
        }
    }
}
