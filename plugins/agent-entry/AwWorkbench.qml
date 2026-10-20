// Apache-2.0; see LICENSE, NOTICE and ORIGIN.md.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "I18n.js" as I18n

Rectangle {
    id: root
    property var report: null
    property string language: "en"
    property bool busy: false
    property bool launcherAvailable: false
    property bool detailsVisible: false
    readonly property var viewData: report || ({state: "loading"})
    readonly property var metrics: viewData.tokenless || ({})
    readonly property var security: viewData.security || ({})
    readonly property bool hasMetrics: metrics.status === "ok" && metrics.records > 0
    function t(key) { return I18n.text(language, key) }
    function policy(component) {
        if (component.configured === false) return t("aw_not_configured")
        return component.enabled === true ? t("aw_enabled") : component.enabled === false ? t("aw_disabled") : t("aw_unknown")
    }
    function number(value) { return Number(value).toLocaleString(Qt.locale(language), "f", 0) }
    signal launchRequested()
    implicitHeight: body.implicitHeight + 36
    radius: 14
    color: "#17263b"
    border.color: "#47658e"

    ColumnLayout {
        id: body
        anchors.fill: parent
        anchors.margins: 18
        spacing: 14
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                Text { text: root.t("aw_heading"); font.pixelSize: 23; font.bold: true; color: "#edf2ff" }
                Text {
                    objectName: "awServiceState"
                    text: root.t("aw_state_" + root.viewData.state)
                    color: root.viewData.state === "online" && root.viewData.audit !== false ? "#89d6b0" : "#dfbf83"
                    font.pixelSize: 14
                }
            }
            EntryButton {
                objectName: "agentAction-aw"
                text: root.launcherAvailable ? root.t("aw_launch") : root.t("install_guide")
                accent: root.launcherAvailable
                enabled: !root.busy
                onClicked: root.launchRequested()
            }
        }
        Text {
            Layout.fillWidth: true
            visible: root.viewData.audit === false
            text: root.t("aw_audit_error")
            wrapMode: Text.WordWrap
            color: "#ffadad"
        }
        GridLayout {
            Layout.fillWidth: true
            columns: root.width >= 820 ? 3 : 1
            columnSpacing: 12
            rowSpacing: 10
            Repeater {
                model: [
                    { title: "Tokenless", value: root.hasMetrics ? root.number(root.metrics.before) + " → " + root.number(root.metrics.after) : "—",
                      detail: root.hasMetrics ? root.t("aw_estimated_tokens") : root.t("aw_metrics_" + (root.metrics.status || "unavailable")),
                      note: root.policy(root.metrics) },
                    { title: root.t("aw_reduction"), value: root.hasMetrics ? Number(root.metrics.percent).toFixed(1) + "%" : "—",
                      detail: root.hasMetrics ? root.number(root.metrics.saved) + " " + root.t("aw_tokens_reduced") : root.t("aw_no_measurement"),
                      note: root.hasMetrics ? root.number(root.metrics.records) + " " + root.t("aw_records") : root.t("aw_no_records") },
                    { title: "sec-core", value: root.policy(root.security),
                      detail: root.t("aw_backend_" + (root.security.backend || "not_checked")),
                      note: root.t("aw_health_boundary") }
                ]
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: fields.implicitHeight + 24
                    radius: 10
                    color: "#111d2e"
                    ColumnLayout {
                        id: fields
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6
                        Text { text: modelData.title; color: "#aabbd6"; font.pixelSize: 13 }
                        Text { text: modelData.value; color: "#edf2ff"; font.pixelSize: 22; font.bold: true; Layout.fillWidth: true; wrapMode: Text.WrapAnywhere }
                        Text { text: modelData.detail; color: "#bdd1ef"; font.pixelSize: 12; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Text { text: modelData.note; color: "#91a6c4"; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    }
                }
            }
        }
        Text {
            Layout.fillWidth: true
            text: root.t("aw_metrics_scope")
            color: "#91a6c4"
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
        RowLayout {
            Text { text: root.t("aw_recent"); color: "#e1ebfb"; font.pixelSize: 14; font.bold: true }
            Item { Layout.fillWidth: true }
            Text { text: root.viewData.updated ? root.t("aw_updated") + " " + root.viewData.updated : ""; color: "#91a6c4"; font.pixelSize: 11 }
        }
        ColumnLayout {
            objectName: "awActivities"
            Layout.fillWidth: true
            spacing: 7
            Repeater {
                model: (root.viewData.activities || []).slice(0, 5)
                delegate: RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    Rectangle { width: 6; height: 6; radius: 3; color: modelData.tone === "danger" ? "#ffadad" : modelData.tone === "notice" ? "#dfbf83" : "#89b2ef" }
                    Text { Layout.fillWidth: true; text: root.t("aw_event_" + modelData.kind); color: "#ccd9ec"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                    Text { text: modelData.elapsed_ms + " ms"; color: "#91a6c4"; font.pixelSize: 11 }
                }
            }
            Text {
                Layout.fillWidth: true
                visible: !(root.viewData.activities || []).length
                text: root.viewData.activity_status === "ok" ? root.t("aw_no_activity") : root.t("aw_activity_unavailable")
                color: "#91a6c4"; font.pixelSize: 12; wrapMode: Text.WordWrap
            }
        }
        Text {
            Layout.fillWidth: true
            text: root.t("aw_permission_note")
            color: "#91a6c4"; font.pixelSize: 11; wrapMode: Text.WordWrap
        }
        EntryButton {
            objectName: "awDetailsToggle"
            text: root.detailsVisible ? root.t("aw_hide_details") : root.t("aw_details")
            quiet: true
            onClicked: root.detailsVisible = !root.detailsVisible
        }
        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: 160
            visible: root.detailsVisible
            clip: true
            TextArea {
                objectName: "awDetails"
                text: JSON.stringify(root.viewData, null, 2)
                readOnly: true
                selectByMouse: true
                textFormat: TextEdit.PlainText
                wrapMode: TextEdit.WrapAnywhere
                color: "#b7c8e5"
                font.pixelSize: 11
                background: Rectangle { color: "#111827" }
            }
        }
    }
}
