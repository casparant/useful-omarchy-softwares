// Apache-2.0; see LICENSE, NOTICE and ORIGIN.md.
import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    property var plan: ({})
    property string language: "en"
    function tr(zh, en) { return language === "zh" ? zh : en }
    function label(role) {
        var labels = {
            security: tr("安全检查", "Security check"),
            optimization: tr("命令优化", "Command optimization"),
            observation: tr("完成观察", "Completion observation"),
            compression: tr("结果压缩", "Result compression"),
            custom: tr("自定义步骤", "Custom step")
        }
        return labels[role] || labels.custom
    }
    spacing: 10
    Text { text: root.tr("Hook 链", "Hook chain"); font.pixelSize: 17; font.bold: true; color: "#ecebe4" }
    Text {
        Layout.fillWidth: true
        text: root.tr("配置顺序 · 原生接入尚未确认", "Configured order · Native attachment unverified")
        color: "#9ba9aa"; font.pixelSize: 12; wrapMode: Text.WordWrap
    }
    Repeater {
        model: root.plan.phases || []
        delegate: ColumnLayout {
            required property var modelData
            readonly property var phase: modelData
            Layout.fillWidth: true
            Text {
                text: (phase.event === "tool.before" ? root.tr("执行前", "Before tool") : root.tr("执行后", "After tool"))
                    + (phase.enabled ? "" : root.tr(" · 未启用", " · Disabled"))
                    + (phase.conditional ? root.tr(" · 按条件", " · Conditional") : "")
                color: "#80c6bc"; font.pixelSize: 12; font.bold: true
            }
            Repeater {
                model: phase.steps
                delegate: Rectangle {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    implicitHeight: stepFields.implicitHeight + 14
                    color: "#202a2e"; radius: 5
                    RowLayout {
                        id: stepFields
                        anchors.fill: parent; anchors.margins: 7
                        Text { text: String(index + 1).padStart(2, "0"); color: "#7b9697"; font.family: "monospace"; font.pixelSize: 11 }
                        Text {
                            Layout.fillWidth: true
                            text: root.label(modelData.role) + (modelData.enabled ? "" : root.tr(" · 未启用", " · Disabled"))
                            color: "#e0e5df"; font.pixelSize: 13; wrapMode: Text.WordWrap
                        }
                        Text {
                            text: modelData.on_error === "block" ? root.tr("异常阻断", "Fail closed")
                                : modelData.on_error === "withhold_result" ? root.tr("异常扣留结果", "Withhold result") : root.tr("异常报告", "Report errors")
                            color: modelData.on_error === "block" ? "#dcbb83" : "#a0adae"; font.pixelSize: 10
                        }
                    }
                }
            }
            Text {
                visible: phase.steps.length === 0
                text: root.tr("没有配置步骤", "No configured steps"); color: "#9ba9aa"; font.pixelSize: 12
            }
        }
    }
    Text {
        visible: root.plan.status !== "configured"
        text: root.tr("暂时无法读取 Hook 配置", "Hook configuration unavailable")
        color: "#dcbb83"; font.pixelSize: 12
    }
}
