// Apache-2.0; see LICENSE, NOTICE and ORIGIN.md.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "I18n.js" as I18n

Rectangle {
    id: root
    color: "#151d21"
    radius: compact ? 12 : 0
    border.color: "#3c4c51"
    property bool compact: true
    property bool busy: false
    property string language: "en"
    property string project: ""
    property string message: ""
    property var aw: null
    property var agents: []
    readonly property var report: aw || ({state: "loading"})
    readonly property var metrics: report.tokenless || ({})
    readonly property var security: report.security || ({})
    readonly property var cosh: agents.find(function(a) { return a.id === "cosh" }) || ({available: false})
    function tr(zh, en) { return language === "zh" ? zh : en }
    function t(key) { return I18n.text(language, key) }
    function policy(component) {
        if (component.configured === false) return t("aw_not_configured")
        return component.enabled === true ? t("aw_enabled")
            : component.enabled === false ? t("aw_disabled") : t("aw_unknown")
    }
    signal actionRequested(var args)
    signal detailsRequested()
    signal catalogRequested()
    signal refreshRequested()
    signal closeRequested()
    Shortcut { sequence: "Escape"; onActivated: root.closeRequested() }

    ScrollView {
        objectName: "controlScroll"
        anchors.fill: parent; anchors.margins: root.compact ? 18 : 28
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: 17
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: "ANOLISA  /  AW"; font.pixelSize: 10; font.letterSpacing: 2; color: "#80c6bc" }
                    Text {
                        objectName: "controlHeading"
                        text: root.tr("Agent 管控面", "Agent control plane")
                        font.pixelSize: root.compact ? 23 : 30; font.bold: true; color: "#f0eee7"
                    }
                }
                EntryButton {
                    objectName: "controlLanguage"
                    text: root.language === "zh" ? "EN" : "中"; quiet: true
                    enabled: !root.busy
                    onClicked: root.actionRequested(["language", root.language === "zh" ? "en" : "zh"])
                }
                EntryButton { text: "×"; quiet: true; onClicked: root.closeRequested() }
            }
            Text {
                objectName: "controlService"
                Layout.fillWidth: true
                text: root.busy ? root.tr("正在读取本地状态…", "Reading local status…") : root.t("aw_state_" + root.report.state)
                color: root.report.state === "online" ? "#80c6bc" : "#dcbb83"; font.pixelSize: 12; wrapMode: Text.WordWrap
            }
            Text {
                visible: root.report.audit === false
                Layout.fillWidth: true; text: root.t("aw_audit_error")
                color: "#efaaaa"; font.pixelSize: 12; wrapMode: Text.WordWrap
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#334146" }
            HookPlan {
                objectName: "controlHooks"
                Layout.fillWidth: true
                language: root.language
                plan: root.report.hook_plan || ({})
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#334146" }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Tokenless"; font.pixelSize: 15; font.bold: true; color: "#ecebe4" }
                    Item { Layout.fillWidth: true }
                    Text {
                        objectName: "controlSavings"
                        text: root.metrics.status === "ok" && root.metrics.records > 0
                            ? Number(root.metrics.saved).toLocaleString(Qt.locale(root.language), "f", 0) + " tokens · " + Number(root.metrics.percent).toFixed(1) + "%"
                            : "—"
                        color: "#80c6bc"; font.pixelSize: 14
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: root.metrics.status === "ok" && root.metrics.records > 0
                        ? root.tr("组件历史估算 · 最多 200 条", "Component history estimate · Up to 200 records")
                        : root.t("aw_metrics_" + (root.metrics.status || "unavailable"))
                    color: "#9ba9aa"; font.pixelSize: 11; wrapMode: Text.WordWrap
                }
                Text {
                    text: root.policy(root.metrics)
                    color: "#9ba9aa"; font.pixelSize: 11
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 7
                Text { text: "sec-core"; font.pixelSize: 15; font.bold: true; color: "#ecebe4" }
                Text {
                    Layout.fillWidth: true
                    text: root.t("aw_backend_" + (root.security.backend || "not_checked"))
                    color: root.security.backend === "authenticated_reachable" ? "#80c6bc" : "#dcbb83"
                    font.pixelSize: 12; wrapMode: Text.WordWrap
                }
                Text {
                    Layout.fillWidth: true; text: root.t("aw_health_boundary")
                    color: "#9ba9aa"; font.pixelSize: 11; wrapMode: Text.WordWrap
                }
                Text { text: root.policy(root.security); color: "#9ba9aa"; font.pixelSize: 11 }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#334146" }
            Text { text: root.tr("策略与会话", "Policy and sessions"); font.pixelSize: 15; font.bold: true; color: "#ecebe4" }
            Text {
                objectName: "controlPolicy"
                Layout.fillWidth: true
                text: root.tr("当前读取文件配置。运行时策略版本、会话绑定和热更新尚未接入。", "Reading file configuration. Active revisions, session binding and policy reload are not connected yet.")
                color: "#9ba9aa"; font.pixelSize: 12; wrapMode: Text.WordWrap
            }
            ColumnLayout {
                visible: !root.compact
                Layout.fillWidth: true; spacing: 12
                Text { text: root.tr("cosh · 一个应用，两种视角", "cosh · One application, two views"); color: "#ecebe4"; font.pixelSize: 20; font.bold: true }
                Text {
                    Layout.fillWidth: true
                    text: root.tr("AI Shell 用于交互；运行视图由 herdr 提供持久终端与 Agent 状态。查看本地状态无需模型登录。", "AI Shell handles interaction; the run view uses herdr for persistent terminals and agent status. Local status does not require model sign-in.")
                    color: "#b7c5c5"; font.pixelSize: 13; wrapMode: Text.WordWrap
                }
                RowLayout {
                    EntryButton {
                        objectName: "controlCosh"
                        text: root.tr("打开 AI Shell", "Open AI Shell"); accent: true
                        accentColor: "#80c6bc"
                        enabled: root.cosh.available && !root.busy
                        onClicked: root.actionRequested(["launch", "cosh", "--project", root.project])
                    }
                    EntryButton {
                        objectName: "controlRunView"
                        text: root.tr("运行视图 · 待接入", "Run view · Planned"); enabled: false
                    }
                }
                Text {
                    Layout.fillWidth: true
                    text: root.cosh.available ? root.tr("已发现 cosh 入口；尚未验证版本和模式切换。", "cosh entry found; version and mode switching are not verified.")
                        : root.tr("尚未安装 cosh；安装方案见设计说明。", "cosh is not installed; see the delivery design.")
                    color: "#dcbb83"; font.pixelSize: 12; wrapMode: Text.WordWrap
                }
                Text { text: root.tr("最近活动 · 当前 AW 服务代次", "Recent activity · Current AW service generation"); color: "#ecebe4"; font.pixelSize: 15; font.bold: true }
                Repeater {
                    model: (root.report.activities || []).slice(0, 5)
                    delegate: RowLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        Text { text: "•"; color: modelData.tone === "danger" ? "#efaaaa" : "#80c6bc" }
                        Text { Layout.fillWidth: true; text: root.t("aw_event_" + modelData.kind); color: "#c6d1d0"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                        Text { text: modelData.elapsed_ms + " ms"; color: "#9ba9aa"; font.pixelSize: 11 }
                    }
                }
                Text {
                    Layout.fillWidth: true
                    visible: !(root.report.activities || []).length
                    text: root.t("aw_activity_unavailable")
                    color: "#9ba9aa"; font.pixelSize: 12; wrapMode: Text.WordWrap
                }
            }
            RowLayout {
                Layout.fillWidth: true
                EntryButton {
                    objectName: "controlCoshCompact"
                    visible: root.compact
                    text: root.tr("打开 AI Shell", "Open AI Shell"); accent: true
                    accentColor: "#80c6bc"
                    enabled: root.cosh.available && !root.busy
                    onClicked: root.actionRequested(["launch", "cosh", "--project", root.project])
                }
                EntryButton {
                    objectName: "controlDetails"
                    Layout.fillWidth: true
                    text: root.compact ? root.tr("查看详情", "View details") : root.tr("软件与安装", "Software and installation")
                    accent: !root.compact
                    accentColor: "#80c6bc"
                    onClicked: root.compact ? root.detailsRequested() : root.catalogRequested()
                }
                EntryButton {
                    objectName: "controlRefresh"
                    text: root.tr("刷新", "Refresh"); enabled: !root.busy
                    onClicked: root.refreshRequested()
                }
            }
            Text {
                Layout.fillWidth: true
                text: root.tr("只读查询 · 不启动后台 · 权限确认保留在 Agent 内", "Read-only · No service startup · Permissions stay in the agent")
                color: "#9ba9aa"; font.pixelSize: 11; wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                visible: root.message !== ""
                text: root.message; textFormat: Text.PlainText
                color: "#dcbb83"; font.pixelSize: 12; wrapMode: Text.WrapAnywhere
            }
        }
    }
}
