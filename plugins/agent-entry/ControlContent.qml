// Apache-2.0; see LICENSE, NOTICE and ORIGIN.md.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "I18n.js" as I18n

Rectangle {
    id: root
    color: "#0c111c"; radius: 16
    border.color: "#2a3650"
    property bool compact: true
    property bool busy: false
    property string language: "en"
    property string project: ""
    property string message: ""
    property var aw: null
    property var runtime: ({state: "unavailable", sessions: []})
    property var agents: []
    property string filter: "all"
    property bool tokenExpanded: false
    property bool securityExpanded: false
    property bool policyExpanded: false
    property var expandedSessions: ({})
    readonly property var boundSessions: sessions.filter(function(s) { return !!s.pid && s.policy === "bound" })
    readonly property var displayedPlan: boundSessions.length === 1 ? boundSessions[0].hook_plan : (report.hook_plan || ({}))
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
        return sessions.filter(function(s) { return !!s.pid && root.componentBound(s, role) }).length
    }
    function componentActivities(role) {
        if (boundSessions.length !== 1) return []
        var kinds = role === "tokenless" ? ["optimization_checked", "optimization_retry", "compression_completed"] : ["security_checked", "security_block", "completion_observed"]
        return (boundSessions[0].activities || []).filter(function(a) { return kinds.includes(a.kind) }).slice(0, 2)
    }
    function stateText(s) {
        var states = {working: tr("正在执行", "Working"), blocked: tr("等待处理", "Needs attention"), idle: tr("等待输入", "Idle"), done: tr("等待输入", "Ready"), exited: tr("已退出", "Exited"), failed: tr("启动失败", "Launch failed"), starting: tr("启动中", "Starting")}
        return states[s] || tr("状态待确认", "State unconfirmed")
    }
    function sessionKey(s) { return s.id || "pid-" + s.pid }
    function toggleSession(s) {
        var next = Object.assign({}, expandedSessions)
        next[sessionKey(s)] = !next[sessionKey(s)]
        expandedSessions = next
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
        anchors.bottomMargin: root.compact ? compactFooter.implicitHeight + 28 : 28
        contentWidth: availableWidth; clip: true
        ColumnLayout {
            width: parent.width; spacing: root.compact ? 11 : 14
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true; Layout.minimumWidth: 0
                    Text { visible: !root.compact; text: "ANOLISA · AGENT WORKBENCH"; color: "#8b93a6"; font.pixelSize: 11; font.letterSpacing: 2 }
                    Text { objectName: "controlHeading"; Layout.fillWidth: true; elide: Text.ElideRight; text: root.compact ? root.tr("AW 管控面", "AW control panel") : root.tr("AW 工作台", "AW workbench"); color: "#ffffff"; font.pixelSize: root.compact ? 22 : 26; font.bold: true }
                }
                Text { visible: root.compact && root.width >= 420; text: root.tr("只读", "Read-only"); color: "#aab7ff"; font.pixelSize: 11 }
                EntryButton {
                    objectName: "controlLanguage"; text: root.language === "zh" ? "EN" : "中"; quiet: true
                    enabled: !root.busy
                    onClicked: root.actionRequested(["language", root.language === "zh" ? "en" : "zh"])
                }
                EntryButton { text: "×"; quiet: true; onClicked: root.closeRequested() }
            }
            Text {
                visible: !root.compact; Layout.fillWidth: true
                text: root.tr("这里呈现 AW 核心组件与 cosh 的协同状态。Agent 在 cosh 中通过 aw run 启动；此面板只读查询与返回会话。", "AW core components and their integration with cosh. Launch agents with aw run inside cosh; this board queries and returns to sessions.")
                color: "#c3c7d4"; font.pixelSize: 14; wrapMode: Text.WordWrap
            }
            Rectangle {
                visible: !root.compact; Layout.fillWidth: true
                implicitHeight: projectLabel.implicitHeight + 20
                color: "#17233a"; border.color: "#2a3650"; radius: 10
                Text { id: projectLabel; anchors.fill: parent; anchors.margins: 10; text: root.tr("项目目录  ", "Project  ") + root.project; textFormat: Text.PlainText; color: "#c3c7d4"; font.pixelSize: 13; wrapMode: Text.WrapAnywhere }
            }
            Rectangle {
                visible: !root.compact; Layout.fillWidth: true
                implicitHeight: entryColumn.implicitHeight + 32
                color: "#121a2b"; border.color: "#2a3650"; radius: 16
                ColumnLayout {
                    id: entryColumn; anchors.fill: parent; anchors.margins: 16; spacing: 10
                    Text { text: root.tr("入口", "ENTRY"); color: "#8b93a6"; font.pixelSize: 12 }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 14
                        Rectangle { width: 52; height: 52; radius: 14; color: "#1d2c47"; Text { anchors.centerIn: parent; text: ">_"; color: "#aab7ff"; font.pixelSize: 23; font.bold: true } }
                        ColumnLayout {
                            Layout.fillWidth: true; Layout.minimumWidth: 0
                            Text { text: "cosh"; color: "white"; font.pixelSize: 20; font.bold: true }
                            Text { Layout.fillWidth: true; text: root.tr("AI Shell · Agent 的统一入口", "AI Shell · One entry for agents"); color: "#c3c7d4"; font.pixelSize: 13; wrapMode: Text.WordWrap }
                            Text { Layout.fillWidth: true; text: "aw run --agent qoder"; color: "#aab7ff"; font.family: "monospace"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                        }
                        ColumnLayout {
                            Text { text: root.cosh.available ? root.tr("◆ 已安装", "◆ Installed") : root.tr("○ 未发现", "○ Not found"); color: root.cosh.available ? "#aab7ff" : "#fab219"; font.pixelSize: 12 }
                            Text { text: root.runtime.state === "online" ? root.tr("herdr 在线", "herdr online") : root.tr("herdr 未连接", "herdr unavailable"); color: "#8b93a6"; font.pixelSize: 11 }
                        }
                        EntryButton { objectName: "controlCosh"; text: root.tr("打开 cosh", "Open cosh"); accent: true; accentColor: "#8b9cff"; enabled: root.cosh.available && !root.busy; onClicked: root.actionRequested(["launch", "cosh", "--project", root.project]) }
                    }
                }
            }
            Rectangle { visible: root.compact; Layout.fillWidth: true; height: 1; color: "#343c51" }
            ColumnLayout {
                visible: root.compact; Layout.fillWidth: true; spacing: 4
                Text { Layout.fillWidth: true; text: root.tr("组件与 Hook · 按需展开", "Components and hooks · Expand for details"); color: "#8b93a6"; font.pixelSize: 12 }
                Text { objectName: "controlService"; Layout.fillWidth: true; text: root.runtime.state === "online" ? root.tr("herdr 在线 · ", "herdr online · ") + root.boundSessions.length + root.tr(" 个会话已绑定 AW", " sessions bound to AW") : root.tr("托管后台未连接", "Session server unavailable"); color: root.runtime.state === "online" ? "#aab7ff" : "#fab219"; font.pixelSize: 11; wrapMode: Text.WordWrap }
            }
            Text { visible: !root.compact; text: root.tr("AW 核心组件", "AW components"); color: "#8b93a6"; font.pixelSize: 12 }
            GridLayout {
                Layout.fillWidth: true
                columns: !root.compact && root.width > 700 ? 2 : 1
                rowSpacing: 10; columnSpacing: 16
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; implicitHeight: tokenColumn.implicitHeight + 24
                    color: "#17233a"; border.color: "#2a3650"; radius: 12
                    ColumnLayout {
                        id: tokenColumn; anchors.fill: parent; anchors.margins: 12; spacing: 5
                        RowLayout {
                            Layout.fillWidth: true
                            Rectangle { visible: !root.compact; width: 34; height: 34; radius: 10; color: "#1d2c47"; Text { anchors.centerIn: parent; text: "⇄"; color: "#aab7ff"; font.pixelSize: 20 } }
                            Text { Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight; text: "Tokenless"; color: "#eff0ff"; font.pixelSize: 16; font.bold: true }
                            Item { Layout.fillWidth: true }
                            Text { text: root.bound("tokenless") > 0 ? root.tr("已绑定 ", "Bound: ") + root.bound("tokenless") : root.tr("接入未确认", "Binding unconfirmed"); color: root.bound("tokenless") > 0 ? "#59d88a" : "#fab219"; font.pixelSize: 11 }
                            EntryButton { objectName: "controlTokenToggle"; text: root.compact ? (root.tokenExpanded ? "⌄" : "›") : (root.tokenExpanded ? root.tr("收起详情", "Hide details") : root.tr("展开详情", "Show details")); quiet: true; onClicked: root.tokenExpanded = !root.tokenExpanded }
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root.metrics.status === "ok" && root.metrics.records > 0
                                ? root.tr("历史估算节省 ", "History estimate: saved ") + Number(root.metrics.saved).toLocaleString(Qt.locale(root.language), "f", 0) + " tokens · " + Number(root.metrics.percent).toFixed(1) + "%"
                                : root.tr("暂无压缩统计", "No compression metrics")
                            color: "#8b93a6"; font.pixelSize: 11; wrapMode: Text.WordWrap
                        }
                        Text {
                            objectName: "controlSavings"
                            visible: !root.compact || root.tokenExpanded
                            Layout.fillWidth: true; wrapMode: Text.WordWrap
                            text: root.metrics.status === "ok" && root.metrics.records > 0 ? Number(root.metrics.before).toLocaleString(Qt.locale(root.language), "f", 0) + " → " + Number(root.metrics.after).toLocaleString(Qt.locale(root.language), "f", 0) : "—"
                            color: "#d1cdff"; font.pixelSize: root.compact ? 16 : 25; font.bold: true
                        }
                        Text { visible: root.tokenExpanded; Layout.fillWidth: true; text: root.tr("组件历史估算 · 非当前会话账单", "Component history estimate · Not session billing"); color: "#8b93a6"; font.pixelSize: 11; wrapMode: Text.WordWrap }
                        Repeater {
                            model: root.tokenExpanded ? root.componentActivities("tokenless") : []
                            delegate: Text {
                                required property var modelData
                                Layout.fillWidth: true
                                text: root.t("aw_event_" + modelData.kind) + " · " + modelData.elapsed_ms + " ms"
                                color: modelData.tone === "danger" ? "#efaaaa" : "#c3c7d4"; font.pixelSize: 11; wrapMode: Text.WordWrap
                            }
                        }
                        Text { visible: root.tokenExpanded; Layout.fillWidth: true; text: root.boundSessions.length === 1 ? root.tr("该受管会话最近步骤 · 只读", "Recent steps in this managed session · Read-only") : root.tr("各会话活动见下方会话详情", "See each session's details for activity"); color: "#8b93a6"; font.pixelSize: 11; wrapMode: Text.WordWrap }
                    }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; implicitHeight: securityColumn.implicitHeight + 24
                    color: "#17233a"; border.color: "#2a3650"; radius: 12
                    ColumnLayout {
                        id: securityColumn; anchors.fill: parent; anchors.margins: 12; spacing: 5
                        RowLayout {
                            Layout.fillWidth: true
                            Rectangle { visible: !root.compact; width: 34; height: 34; radius: 10; color: "#1d2c47"; Text { anchors.centerIn: parent; text: "◇"; color: "#aab7ff"; font.pixelSize: 20 } }
                            Text { Layout.fillWidth: true; Layout.minimumWidth: 0; elide: Text.ElideRight; text: "sec-core"; color: "#eff0ff"; font.pixelSize: 16; font.bold: true }
                            Item { Layout.fillWidth: true }
                            Text { text: root.bound("security") > 0 ? root.tr("已绑定 ", "Bound: ") + root.bound("security") : root.tr("接入未确认", "Binding unconfirmed"); color: root.bound("security") > 0 ? "#59d88a" : "#fab219"; font.pixelSize: 11 }
                            EntryButton { objectName: "controlSecurityToggle"; text: root.compact ? (root.securityExpanded ? "⌄" : "›") : (root.securityExpanded ? root.tr("收起详情", "Hide details") : root.tr("展开详情", "Show details")); quiet: true; onClicked: root.securityExpanded = !root.securityExpanded }
                        }
                        Text { Layout.fillWidth: true; text: root.t("aw_backend_" + (root.security.backend || "not_checked")); color: root.security.backend === "authenticated_reachable" ? "#59d88a" : "#fab219"; font.pixelSize: root.compact ? 12 : 17; wrapMode: Text.WordWrap }
                        Text { visible: !root.compact || root.securityExpanded; Layout.fillWidth: true; text: root.tr("后台可达 ≠ 调用安全结论", "Backend health ≠ Call admission"); color: "#8b93a6"; font.pixelSize: 11; wrapMode: Text.WordWrap }
                        Repeater {
                            model: root.securityExpanded ? root.componentActivities("security") : []
                            delegate: Text {
                                required property var modelData
                                Layout.fillWidth: true
                                text: root.t("aw_event_" + modelData.kind) + " · " + modelData.elapsed_ms + " ms"
                                color: modelData.tone === "danger" ? "#efaaaa" : "#c3c7d4"; font.pixelSize: 11; wrapMode: Text.WordWrap
                            }
                        }
                        Text { visible: root.securityExpanded; Layout.fillWidth: true; text: root.boundSessions.length === 1 ? root.tr("该受管会话最近步骤 · 只读", "Recent steps in this managed session · Read-only") : root.tr("各会话活动见下方会话详情", "See each session's details for activity"); color: "#8b93a6"; font.pixelSize: 11; wrapMode: Text.WordWrap }
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true; implicitHeight: policyColumn.implicitHeight + 20
                radius: 8; color: "#17233a"; border.color: "#2a3650"
                ColumnLayout {
                    id: policyColumn; anchors.fill: parent; anchors.margins: 10; spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: root.tr("策略", "Policy"); color: "#ffffff"; font.pixelSize: 14; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Text { text: root.tr("每会话固定版本", "Frozen per session"); color: "#8b93a6"; font.pixelSize: 11 }
                        EntryButton { objectName: "controlPolicyToggle"; text: root.policyExpanded ? "⌄" : "›"; quiet: true; onClicked: root.policyExpanded = !root.policyExpanded }
                    }
                    Text { visible: root.policyExpanded; Layout.fillWidth: true; text: root.tr("已绑定须核验原生 Hook 与 AW 实例一致。新配置用于新会话；热更新和 VM 重启续接尚未启用。", "Bound requires matching native hooks and AW instance. New configuration applies to new sessions. Hot reload and VM reboot restore are not enabled."); color: "#8b93a6"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                }
            }
            Rectangle {
                visible: root.compact && root.policyExpanded; Layout.fillWidth: true
                implicitHeight: compactHooks.implicitHeight + 24
                color: "#17233a"; border.color: "#2a3650"; radius: 10
                HookPlan {
                    id: compactHooks; objectName: "compactHooks"
                    anchors.fill: parent; anchors.margins: 12
                    compact: true; language: root.language; plan: root.displayedPlan || ({})
                    evidence: root.boundSessions.length === 1
                        ? root.tr("会话绑定已核验 · ", "Session binding verified · ") + String(root.boundSessions[0].revision).slice(0, 10)
                        : root.tr("默认配置顺序 · 各会话绑定见下方", "Default configuration · See session bindings below")
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text { text: root.tr("当前会话", "CURRENT SESSIONS"); color: "#eff0ff"; font.pixelSize: 15; font.bold: true }
                Item { Layout.fillWidth: true }
                Text { text: root.runtime.updated || ""; color: "#8b93a6"; font.pixelSize: 11 }
            }
            RowLayout {
                visible: !root.compact
                Repeater {
                    model: [{id: "all", zh: "全部", en: "All"}, {id: "bound", zh: "已绑定", en: "Bound"}, {id: "unknown", zh: "未确认", en: "Unconfirmed"}]
                    delegate: EntryButton {
                        required property var modelData
                        text: root.tr(modelData.zh, modelData.en); accent: root.filter === modelData.id; accentColor: "#8b9cff"
                        onClicked: root.filter = modelData.id
                    }
                }
            }
            Repeater {
                model: root.filtered()
                delegate: Rectangle {
                    id: sessionCard
                    required property var modelData
                    readonly property bool expanded: !!root.expandedSessions[root.sessionKey(modelData)]
                    objectName: "session-" + root.sessionKey(modelData)
                    Layout.fillWidth: true; implicitHeight: sessionColumn.implicitHeight + 26
                    color: "#17233a"; radius: 10
                    border.color: modelData.policy === "bound" ? "#328451" : (modelData.state === "exited" ? "#35425b" : "#94732c")
                    ColumnLayout {
                        id: sessionColumn
                        anchors.fill: parent; anchors.margins: 13; spacing: 7
                        RowLayout {
                            Layout.fillWidth: true
                            Text { Layout.fillWidth: true; text: modelData.agent + " · " + root.stateText(modelData.state); textFormat: Text.PlainText; color: "#eff0ff"; font.pixelSize: 14; font.bold: true; wrapMode: Text.WordWrap }
                            EntryButton {
                                visible: !root.compact; objectName: "sessionDetails-" + root.sessionKey(modelData)
                                text: sessionCard.expanded ? root.tr("收起详情", "Hide details") : root.tr("展开详情", "Show details"); quiet: true
                                onClicked: root.toggleSession(modelData)
                            }
                            EntryButton {
                                text: root.tr("返回", "Return"); quiet: true
                                enabled: !!modelData.pid && !!modelData.id && modelData.policy !== "unmanaged" && !root.busy
                                onClicked: root.actionRequested(["return-session", modelData.id, "--project", modelData.project])
                            }
                        }
                        Text { Layout.fillWidth: true; text: (root.compact ? (modelData.pane || "—") + " · " : "") + (modelData.project || root.tr("项目未确认", "Project unconfirmed")); textFormat: Text.PlainText; color: "#c3c7d4"; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.policy === "bound" ? root.tr("AW Hook 已绑定 · ", "AW hooks bound · ") + String(modelData.revision).slice(0, 10) : modelData.policy === "unmanaged" ? root.tr("未托管 / AW 未确认", "Unmanaged / AW unconfirmed") : root.tr("AW 接入未确认", "AW binding unconfirmed")
                            color: modelData.policy === "bound" ? "#59d88a" : "#fab219"; font.pixelSize: 12; wrapMode: Text.WordWrap
                        }
                        Text {
                            visible: !root.compact; Layout.fillWidth: true
                            text: "Tokenless: " + root.componentText(modelData, "tokenless") + " · sec-core: " + root.componentText(modelData, "security")
                            color: "#c3c7d4"; font.pixelSize: 11; wrapMode: Text.WordWrap
                        }
                        Text {
                            visible: !root.compact && sessionCard.expanded; Layout.fillWidth: true
                            text: root.tr("对话 ", "Conversation ") + (modelData.conversation || "—") + " · PID " + (modelData.pid || "—") + " · " + modelData.pane
                            color: "#8b93a6"; font.pixelSize: 11; wrapMode: Text.WrapAnywhere
                        }
                        HookPlan {
                            visible: !root.compact && sessionCard.expanded && !!modelData.hook_plan; Layout.fillWidth: true
                            language: root.language; plan: modelData.hook_plan || ({})
                            evidence: modelData.policy === "bound" ? root.tr("原生 Hook 与当前 AW 实例匹配", "Native hooks match this AW instance") : ""
                        }
                        Text {
                            visible: !!modelData.security && modelData.security.backend !== "authenticated_reachable"
                            Layout.fillWidth: true; text: root.tr("安全后台不可达 / 未确认；查看原生终端的执行结果", "Security backend unavailable / unconfirmed; check the native terminal")
                            color: "#fab219"; font.pixelSize: 11; wrapMode: Text.WordWrap
                        }
                        Text {
                            visible: !root.compact && sessionCard.expanded && !!modelData.generation; Layout.fillWidth: true
                            text: root.tr("AW 运行代次 ", "AW generation ") + (modelData.generation || "—")
                            color: "#8b93a6"; font.pixelSize: 11; wrapMode: Text.WrapAnywhere
                        }
                        Repeater {
                            model: !root.compact && sessionCard.expanded ? (modelData.activities || []).slice(0, 3) : []
                            delegate: Text {
                                required property var modelData
                                Layout.fillWidth: true
                                text: root.t("aw_event_" + modelData.kind) + " · " + modelData.elapsed_ms + " ms"
                                color: modelData.tone === "danger" ? "#efaaaa" : "#c3c7d4"; font.pixelSize: 11; wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
            Text {
                visible: root.filtered().length === 0; Layout.fillWidth: true
                text: root.runtime.state === "online" ? root.tr("没有匹配的受管会话。在 cosh 中运行 aw run --agent qoder。", "No matching sessions. Run aw run --agent qoder inside cosh.") : root.tr("无法读取托管会话；未保留旧的已绑定状态。", "Cannot query sessions; previous binding state has been cleared.")
                color: "#8b93a6"; font.pixelSize: 12; wrapMode: Text.WordWrap
            }
            ColumnLayout {
                visible: !root.compact && root.policyExpanded; Layout.fillWidth: true; spacing: 12
                Text { objectName: "controlPolicy"; Layout.fillWidth: true; text: root.tr("每个会话固定策略；原生 Hook 绑定与 AW 实例一致才显示已绑定。新配置用于新会话，热更新与 VM 重启续接未启用。", "Policy is frozen per session. Bound requires native hooks matching the AW instance. New configuration applies to new sessions; hot reload and reboot restore are disabled."); color: "#8b93a6"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                HookPlan { objectName: "controlHooks"; Layout.fillWidth: true; language: root.language; plan: root.report.hook_plan || ({}) }
                Text { Layout.fillWidth: true; text: root.tr("上方为默认文件配置；会话卡片显示各自的固定版本。运行状态来自 herdr 终端识别，AW 原生采用状态仍为 unverified。", "Above is the default file configuration; session cards show frozen revisions. Agent state is screen-detected by herdr; AW native adoption remains unverified."); color: "#8b93a6"; font.pixelSize: 11; wrapMode: Text.WordWrap }
            }
            RowLayout {
                visible: !root.compact; Layout.fillWidth: true
                EntryButton { objectName: "controlCatalog"; Layout.fillWidth: true; text: root.tr("软件与安装", "Software and installation"); onClicked: root.catalogRequested() }
                EntryButton { visible: !root.compact; objectName: "controlRefresh"; text: root.tr("刷新", "Refresh"); enabled: !root.busy; onClicked: root.refreshRequested() }
            }
            Text { visible: !root.compact; Layout.fillWidth: true; text: root.tr("AI Shell 为 cosh · 关闭面板不停止会话 · 原生权限", "AI Shell is cosh · Closing panel keeps sessions · Native permissions"); color: "#8b93a6"; font.pixelSize: 11; wrapMode: Text.WordWrap }
            Text { visible: !root.compact && root.message !== ""; Layout.fillWidth: true; text: root.message; textFormat: Text.PlainText; color: "#fab219"; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
        }
    }
    ColumnLayout {
        id: compactFooter
        visible: root.compact
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        anchors.margins: 18; spacing: 7
        Rectangle { Layout.fillWidth: true; height: 1; color: "#2a3650" }
        RowLayout {
            Layout.fillWidth: true
            EntryButton { objectName: "controlCoshCompact"; Layout.fillWidth: true; text: root.tr("打开 AI Shell", "Open AI Shell"); accent: true; accentColor: "#8b9cff"; enabled: root.cosh.available && !root.busy; onClicked: root.actionRequested(["launch", "cosh", "--project", root.project]) }
            EntryButton { objectName: "controlDetails"; Layout.fillWidth: true; text: root.tr("查看详情", "View details"); onClicked: root.detailsRequested() }
        }
        Text { Layout.fillWidth: true; text: root.tr("AI Shell 为 cosh · 关闭面板不停止会话 · 原生权限", "AI Shell is cosh · Closing panel keeps sessions · Native permissions"); color: "#8b93a6"; font.pixelSize: 11; wrapMode: Text.WordWrap }
        Text { visible: root.message !== ""; Layout.fillWidth: true; text: root.message; textFormat: Text.PlainText; color: "#fab219"; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
    }

}
