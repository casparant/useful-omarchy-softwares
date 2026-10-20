// Modified 2026-10-19: persistent language and localized async feedback. Apache-2.0; see ORIGIN.md.
import QtQuick
import Quickshell
import Quickshell.Io
import "I18n.js" as I18n

Item {
    id: root
    property var shell: null
    property var manifest: null
    readonly property bool opened: window.visible
    readonly property string helper: decodeURIComponent(Qt.resolvedUrl("agent_entry.py").toString().replace(/^file:\/\//, ""))
    property string statusError: ""
    property string actionError: ""

    function open(payload) {
        window.visible = true
        refresh()
    }
    function close() { window.visible = false }
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
                    if (result.error) content.message = result.error
                    else {
                        content.agents = result.agents
                        content.aw = result.aw
                        content.project = result.project
                        content.configPath = result.config
                    }
                } catch (e) { content.aw = { state: "query_failed" }; content.message = I18n.text(content.language, "status_error") + String(e) }
            }
        }
        stderr: StdioCollector { onStreamFinished: root.statusError = text }
        onExited: function(code, status) {
            if (code !== 0) { content.aw = { state: "query_failed" }; content.message = root.statusError || I18n.text(content.language, "status_error") }
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
            if (code === 0 && actionProcess.command[2] === "launch") root.close()
            if (code !== 0 && root.actionError) content.message = root.actionError
            refreshTimer.restart()
        }
    }
    Timer { interval: 5000; repeat: true; running: window.visible; onTriggered: root.refresh() }
    Timer { id: refreshTimer; interval: 200; onTriggered: root.refresh() }

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
