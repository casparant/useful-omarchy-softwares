// Apache-2.0; see LICENSE, NOTICE and ORIGIN.md.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "I18n.js" as I18n

Rectangle {
    id: root
    color: "#171b27"; radius: compact ? 16 : 0
    border.color: "#394159"
    property bool compact: true
    property bool busy: false
    property string language: "en"
    property string project: ""
    property string message: ""
    property var aw: null
    property var runtime: ({state: "unavailable", sessions: []})
    property var agents: []
    property string filter: "all"
    readonly property var report: aw || ({state: "loading"})
    readonly property var metrics: report.tokenless || ({})
    readonly property var security: report.security || ({})
    readonly property var sessions: runtime.state === "online" ? (runtime.sessions || []) : []
    readonly property var cosh: agents.find(function(a) { return a.id === "cosh" }) || ({available: false})
    function tr(zh, en) { return language === "zh" ? zh : en }
    function t(key) { return I18n.text(language, key) }
    function componentBound(s, role) {
        var names = role === "tokenless" ? ["optimization", "compression"] : ["security", "observation"]
        return s.policy === "bound" && s[role] && s[role].enabled === true &&
            ((s.hook_plan || {}).phases || []).some(function(p) {
                return p.enabled && p.steps.some(function(step) { return step.enabled && names.includes(step.role) })
            })
    }
    function componentText(s, role) {
        if (s[role] && s[role].enabled === false) return tr("已关闭", "Disabled")
        return componentBound(s, role) ? tr("Hook 已绑定", "Hooks bound") : tr("未确认", "Unconfirmed")
    }
    function bound(role) {
        return sessions.filter(function(s) { return root.componentBound(s, role) }).length
    }
    function stateText(s) {
        var states = {working: tr("正在执行", "Working"), blocked: tr("等待处理", "Needs attention"), idle: tr("等待输入", "Idle"), done: tr("等待输入", "Ready"), exited: tr("已退出", "Exited"), failed: tr("启动失败", "Launch failed"), starting: tr("启动中", "Starting")}
        return states[s] || tr("状态待确认", "State unconfirmed")
    }
    function filtered() {
        return sessions.filter(function(s) { return !(root.compact && s.state === "exited") && (root.filter === "all" || (root.filter === "bound" ? s.policy === "bound" : s.policy !== "bound")) })
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
        contentWidth: availableWidth; clip: true
        ColumnLayout {
            width: parent.width; spacing: root.compact ? 13 : 20
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Text { visible: !root.compact; text: "ANOLISA · AGENT WORKBENCH"; color: "#a7b3d2"; font.pixelSize: 11; font.letterSpacing: 2 }
                    Text { objectName: "controlHeading"; text: root.tr("AW 工作台", "AW workbench"); color: "#f2f1ff"; font.pixelSize: root.compact ? 22 : 32; font.bold: true }
                }
                Item { Layout.fillWidth: true }
                EntryButton {
                    objectName: "controlLanguage"; text: root.language === "zh" ? "EN" : "中"; quiet: true
                    enabled: !root.busy
                    onClicked: root.actionRequested(["language", root.language === "zh" ? "en" : "zh"])
                }
                EntryButton { text: "×"; quiet: true; onClicked: root.closeRequested() }
            }
            Text {
                visible: !root.compact; Layout.fillWidth: true
                text: root.tr("从 cosh 开始与返回 Agent 会话；这里展示真实运行状态和 AW 接入证据。", "Start and return to agents in cosh. This view shows live sessions and AW binding evidence.")
                color: "#b2bbd2"; font.pixelSize: 14; wrapMode: Text.WordWrap
            }
            Text {
                visible: !root.compact; Layout.fillWidth: true
                text: root.tr("项目目录  ", "Project  ") + root.project
                color: "#c8cee2"; font.pixelSize: 13; wrapMode: Text.WrapAnywhere
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#343c51" }
            RowLayout {
                Layout.fillWidth: true; spacing: 12
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 3
                    Text { text: "cosh"; color: "#f2f1ff"; font.pixelSize: 21; font.bold: true }
                    Text { Layout.fillWidth: true; text: root.tr("AI Shell · Agent 统一入口", "AI Shell · Agent entry"); color: "#b2bbd2"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                    Text { objectName: "controlService"; text: root.runtime.state === "online" ? root.tr("herdr 托管后台在线", "herdr server online") : root.tr("托管后台未连接", "Session server unavailable"); color: root.runtime.state === "online" ? "#99d8b5" : "#e4c186"; font.pixelSize: 11 }
                }
                EntryButton {
                    objectName: "controlCosh"
                    text: root.tr("打开 cosh", "Open cosh"); accent: true; accentColor: "#aaa6ff"
                    enabled: root.cosh.available && !root.busy
                    onClicked: root.actionRequested(["launch", "cosh", "--project", root.project])
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#343c51" }
            Text { text: root.tr("AW 核心组件", "AW components"); color: "#a7b3d2"; font.pixelSize: 12 }
            GridLayout {
                Layout.fillWidth: true
                columns: !root.compact && root.width > 700 ? 2 : 1
                rowSpacing: 10; columnSpacing: 16
                Rectangle {
                    Layout.fillWidth: true; implicitHeight: tokenColumn.implicitHeight + (root.compact ? 0 : 24)
                    color: root.compact ? "transparent" : "#22283a"; radius: 12
                    ColumnLayout {
                        id: tokenColumn; anchors.fill: parent; anchors.margins: root.compact ? 0 : 12; spacing: 5
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "Tokenless"; color: "#eff0ff"; font.pixelSize: 16; font.bold: true }
                            Item { Layout.fillWidth: true }
                            Text { text: root.bound("tokenless") > 0 ? root.tr("已绑定 ", "Bound: ") + root.bound("tokenless") : root.tr("接入未确认", "Binding unconfirmed"); color: root.bound("tokenless") > 0 ? "#99d8b5" : "#e4c186"; font.pixelSize: 11 }
                        }
                        Text {
                            objectName: "controlSavings"
                            text: root.metrics.status === "ok" && root.metrics.records > 0 ? Number(root.metrics.before).toLocaleString(Qt.locale(root.language), "f", 0) + " → " + Number(root.metrics.after).toLocaleString(Qt.locale(root.language), "f", 0) : "—"
                            color: "#d1cdff"; font.pixelSize: root.compact ? 16 : 25; font.bold: true
                        }
                        Text { Layout.fillWidth: true; text: root.tr("组件历史估算 · 非当前会话账单", "Component history estimate · Not session billing"); color: "#a7b3d2"; font.pixelSize: 11; wrapMode: Text.WordWrap }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; implicitHeight: securityColumn.implicitHeight + (root.compact ? 0 : 24)
                    color: root.compact ? "transparent" : "#22283a"; radius: 12
                    ColumnLayout {
                        id: securityColumn; anchors.fill: parent; anchors.margins: root.compact ? 0 : 12; spacing: 5
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: "sec-core"; color: "#eff0ff"; font.pixelSize: 16; font.bold: true }
                            Item { Layout.fillWidth: true }
                            Text { text: root.bound("security") > 0 ? root.tr("已绑定 ", "Bound: ") + root.bound("security") : root.tr("接入未确认", "Binding unconfirmed"); color: root.bound("security") > 0 ? "#99d8b5" : "#e4c186"; font.pixelSize: 11 }
                        }
                        Text { Layout.fillWidth: true; text: root.t("aw_backend_" + (root.security.backend || "not_checked")); color: root.security.backend === "authenticated_reachable" ? "#99d8b5" : "#e4c186"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                        Text { Layout.fillWidth: true; text: root.tr("后台可达 ≠ 调用安全结论", "Backend health ≠ Call admission"); color: "#a7b3d2"; font.pixelSize: 11; wrapMode: Text.WordWrap }
                    }
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#343c51" }
            RowLayout {
                Layout.fillWidth: true
                Text { text: root.tr("Agent 会话", "Agent sessions"); color: "#eff0ff"; font.pixelSize: 15; font.bold: true }
                Item { Layout.fillWidth: true }
                Text { text: root.runtime.updated || ""; color: "#a7b3d2"; font.pixelSize: 11 }
            }
            RowLayout {
                visible: !root.compact
                Repeater {
                    model: [{id: "all", zh: "全部", en: "All"}, {id: "bound", zh: "已绑定", en: "Bound"}, {id: "unknown", zh: "未确认", en: "Unconfirmed"}]
                    delegate: EntryButton {
                        required property var modelData
                        text: root.tr(modelData.zh, modelData.en); accent: root.filter === modelData.id; accentColor: "#aaa6ff"
                        onClicked: root.filter = modelData.id
                    }
                }
            }
            Repeater {
                model: root.filtered()
                delegate: Rectangle {
                    required property var modelData
                    Layout.fillWidth: true; implicitHeight: sessionColumn.implicitHeight + 26
                    color: "#22283a"; radius: 12
                    border.color: modelData.policy === "bound" ? "#577c6d" : "#655d45"
                    ColumnLayout {
                        id: sessionColumn
                        anchors.fill: parent; anchors.margins: 13; spacing: 7
                        RowLayout {
                            Layout.fillWidth: true
                            Text { Layout.fillWidth: true; text: modelData.agent + " · " + root.stateText(modelData.state); textFormat: Text.PlainText; color: "#eff0ff"; font.pixelSize: 14; font.bold: true; wrapMode: Text.WordWrap }
                            EntryButton {
                                text: root.tr("返回", "Return"); quiet: true
                            enabled: !!modelData.pid && !!modelData.id && modelData.policy !== "unmanaged" && !root.busy
                                onClicked: root.actionRequested(["return-session", modelData.id, "--project", modelData.project])
                            }
                        }
                        Text { Layout.fillWidth: true; text: modelData.project || root.tr("项目未确认", "Project unconfirmed"); textFormat: Text.PlainText; color: "#b2bbd2"; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.policy === "bound" ? root.tr("AW Hook 已绑定 · ", "AW hooks bound · ") + String(modelData.revision).slice(0, 10) : modelData.policy === "unmanaged" ? root.tr("未托管 / AW 未确认", "Unmanaged / AW unconfirmed") : root.tr("AW 接入未确认", "AW binding unconfirmed")
                            color: modelData.policy === "bound" ? "#99d8b5" : "#e4c186"; font.pixelSize: 12; wrapMode: Text.WordWrap
                        }
                        Text {
                            Layout.fillWidth: true
                            text: "Tokenless: " + root.componentText(modelData, "tokenless") + " · sec-core: " + root.componentText(modelData, "security")
                            color: "#b2bbd2"; font.pixelSize: 11; wrapMode: Text.WordWrap
                        }
                        Text {
                            visible: !root.compact; Layout.fillWidth: true
                            text: root.tr("对话 ", "Conversation ") + (modelData.conversation || "—") + " · PID " + (modelData.pid || "—") + " · " + modelData.pane
                            color: "#a7b3d2"; font.pixelSize: 11; wrapMode: Text.WrapAnywhere
                        }
                        HookPlan {
                            visible: !root.compact && !!modelData.hook_plan; Layout.fillWidth: true
                            language: root.language; plan: modelData.hook_plan || ({})
                        }
                        Text {
                            visible: !!modelData.security && modelData.security.backend !== "authenticated_reachable"
                            Layout.fillWidth: true; text: root.tr("安全后台不可达 / 未确认；查看原生终端的执行结果", "Security backend unavailable / unconfirmed; check the native terminal")
                            color: "#e4c186"; font.pixelSize: 11; wrapMode: Text.WordWrap
                        }
                        Text {
                            visible: !root.compact && !!modelData.generation; Layout.fillWidth: true
                            text: root.tr("AW 运行代次 ", "AW generation ") + (modelData.generation || "—")
                            color: "#a7b3d2"; font.pixelSize: 11; wrapMode: Text.WrapAnywhere
                        }
                        Repeater {
                            model: root.compact ? [] : (modelData.activities || []).slice(0, 3)
                            delegate: Text {
                                required property var modelData
                                Layout.fillWidth: true
                                text: root.t("aw_event_" + modelData.kind) + " · " + modelData.elapsed_ms + " ms"
                                color: modelData.tone === "danger" ? "#efaaaa" : "#b2bbd2"; font.pixelSize: 11; wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
            Text {
                visible: root.filtered().length === 0; Layout.fillWidth: true
                text: root.runtime.state === "online" ? root.tr("没有匹配的受管会话。在 cosh 中运行 aw run --agent qoder。", "No matching sessions. Run aw run --agent qoder inside cosh.") : root.tr("无法读取托管会话；未保留旧的已绑定状态。", "Cannot query sessions; previous binding state has been cleared.")
                color: "#a7b3d2"; font.pixelSize: 12; wrapMode: Text.WordWrap
            }
            ColumnLayout {
                visible: !root.compact; Layout.fillWidth: true; spacing: 12
                Text { objectName: "controlPolicy"; Layout.fillWidth: true; text: root.tr("每个会话固定策略；原生 Hook 绑定与 AW 实例一致才显示已绑定。新配置用于新会话，热更新与 VM 重启续接未启用。", "Policy is frozen per session. Bound requires native hooks matching the AW instance. New configuration applies to new sessions; hot reload and reboot restore are disabled."); color: "#a7b3d2"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                HookPlan { objectName: "controlHooks"; Layout.fillWidth: true; language: root.language; plan: root.report.hook_plan || ({}) }
                Text { Layout.fillWidth: true; text: root.tr("上方为默认文件配置；会话卡片显示各自的固定版本。运行状态来自 herdr 终端识别，AW 原生采用状态仍为 unverified。", "Above is the default file configuration; session cards show frozen revisions. Agent state is screen-detected by herdr; AW native adoption remains unverified."); color: "#a7b3d2"; font.pixelSize: 11; wrapMode: Text.WordWrap }
            }
            RowLayout {
                Layout.fillWidth: true
                EntryButton { objectName: "controlDetails"; Layout.fillWidth: true; text: root.compact ? root.tr("查看详情", "View details") : root.tr("软件与安装", "Software and installation"); onClicked: root.compact ? root.detailsRequested() : root.catalogRequested() }
                EntryButton { objectName: "controlRefresh"; text: root.tr("刷新", "Refresh"); enabled: !root.busy; onClicked: root.refreshRequested() }
            }
            Text { Layout.fillWidth: true; text: root.tr("只读查询 · 关闭面板不停止会话 · 权限留在 Agent 内", "Read-only · Closing this panel keeps sessions · Native permissions"); color: "#a7b3d2"; font.pixelSize: 11; wrapMode: Text.WordWrap }
            Text { visible: root.message !== ""; Layout.fillWidth: true; text: root.message; textFormat: Text.PlainText; color: "#e4c186"; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
        }
    }
}
