// Modified 2026-10-19: English/Chinese interface and persistent language action.
// Modified 2026-10-20: third card action that installs catalog software in a terminal.
// Apache-2.0; see LICENSE, NOTICE and ORIGIN.md.
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import "I18n.js" as I18n

Rectangle {
    id: root
    color: "#111827"
    property var agents: []
    property var aw: null
    property string project: ""
    property string configPath: ""
    property string language: Qt.locale().name.toLowerCase().indexOf("zh") === 0 ? "zh" : "en"
    property string message: ""
    function t(key) { return I18n.text(language, key) }
    property bool busy: false
    signal actionRequested(var args)
    signal refreshRequested()
    signal closeRequested()
    function terminalAvailable() {
        for (var i = 0; i < agents.length; i++) if (agents[i].id === "cosh") return agents[i].available
        return false
    }
    Shortcut { sequence: "Escape"; enabled: !registerDialog.visible; onActivated: root.closeRequested() }

    ScrollView {
        objectName: "dashboardScroll"
        anchors.fill: parent
        anchors.margins: 28
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: parent.width
            spacing: 20

            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    spacing: 5
                    Text { text: "ANOLISA  /  AGENT ENTRY"; color: "#8babf5"; font.pixelSize: 12; font.letterSpacing: 1.5 }
                    Text { objectName: "heading"; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: root.t("heading"); color: "#f2f5ff"; font.pixelSize: 27; font.bold: true }
                    Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: root.t("tagline"); color: "#9cabc4"; font.pixelSize: 13 }
                }
                EntryButton { objectName: "addEntry"; text: root.t("add"); onClicked: registerDialog.open() }
                EntryButton { text: root.t("refresh"); enabled: !root.busy; onClicked: root.refreshRequested() }
                EntryButton { text: root.t("close"); quiet: true; onClicked: root.closeRequested() }
                EntryButton {
                    objectName: "languageToggle"
                    text: root.language === "zh" ? "English" : "中文"
                    enabled: !root.busy
                    onClicked: root.actionRequested(["language", root.language === "zh" ? "en" : "zh"])
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Text { text: root.t("project"); color: "#b4c1d7"; font.pixelSize: 13 }
                EntryField {
                    id: projectField
                    objectName: "projectField"
                    Layout.fillWidth: true
                    text: root.project
                    placeholderText: "/home/you/Projects/example"
                    onAccepted: root.actionRequested(["project", text])
                }
                EntryButton { text: root.t("save_project"); enabled: !root.busy; onClicked: root.actionRequested(["project", projectField.text]) }
            }

            AwWorkbench {
                objectName: "awWorkbench"
                Layout.fillWidth: true
                language: root.language
                report: root.aw
                busy: root.busy
                onGuideRequested: root.actionRequested(["docs", "aw", "--project", projectField.text])
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: hero.implicitHeight + 36
                color: "#1c2940"
                radius: 14
                border.color: "#3a527c"
                RowLayout {
                    id: hero
                    anchors.fill: parent
                    anchors.margins: 18
                    spacing: 20
                    Rectangle {
                        width: 64; height: 64; radius: 12; color: "#101b30"
                        Text { anchors.centerIn: parent; text: ">_"; font.pixelSize: 26; color: "#9abaff"; font.family: "monospace" }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 7
                        Text { text: root.t("terminal_heading"); font.pixelSize: 19; font.bold: true; color: "#edf2ff" }
                        Text {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            text: root.t("terminal_description")
                            color: "#a9b9d3"; font.pixelSize: 13
                        }
                        Text { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: root.terminalAvailable() ? root.t("terminal_ready") : root.t("terminal_missing"); color: "#8da8d4"; font.pixelSize: 12 }
                    }
                    ColumnLayout {
                        Layout.minimumWidth: 166
                        spacing: 9
                        EntryButton { Layout.fillWidth: true; text: root.t("open_cosh"); accent: true; enabled: root.terminalAvailable() && !root.busy; onClicked: root.actionRequested(["launch", "cosh", "--project", projectField.text]) }
                        EntryButton { objectName: "openTerminal"; Layout.fillWidth: true; text: root.t("open_terminal"); enabled: !root.busy; onClicked: root.actionRequested(["launch", "terminal", "--project", projectField.text]) }
                    }
                }
            }

            RowLayout {
                Text { text: root.t("choose"); color: "#e8eefc"; font.pixelSize: 18; font.bold: true }
                Item { Layout.fillWidth: true }
                Text { text: root.t("agent_types"); color: "#8798b5"; font.pixelSize: 12 }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width >= 1080 ? 4 : 2
                columnSpacing: 14
                rowSpacing: 14
                Repeater {
                    model: root.agents.filter(function(agent) { return agent.id !== "cosh" && agent.id !== "aw" })
                    delegate: Rectangle {
                        id: card
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.minimumWidth: 210
                        implicitHeight: 182
                        radius: 12
                        color: "#1a2436"
                        border.color: "#303e56"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 9
                            RowLayout {
                                Text { text: card.modelData.name; color: "#edf2ff"; font.pixelSize: 18; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                Rectangle { width: 7; height: 7; radius: 4; color: card.modelData.available ? "#89d6b0" : "#b5a174" }
                            }
                            Text { text: card.modelData.subtitle; color: "#9dacbf"; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                            Text { text: card.modelData.status; color: card.modelData.available ? "#89d6b0" : "#c0a775"; font.pixelSize: 12 }
                            Item { Layout.fillHeight: true }
                            RowLayout {
                                spacing: 8
                                EntryButton {
                                    objectName: "agentAction-" + card.modelData.id
                                    Layout.fillWidth: true
                                    readonly property bool canInstall: !card.modelData.available && !!card.modelData.installable
                                    text: card.modelData.available ? root.t("open") : canInstall ? root.t("install") : root.t("install_guide")
                                    accent: card.modelData.available || canInstall
                                    enabled: !root.busy && (card.modelData.available || canInstall || !!card.modelData.docs)
                                    onClicked: {
                                        var action = card.modelData.available ? "launch" : canInstall ? "install" : "docs"
                                        root.actionRequested([action, card.modelData.id, "--project", projectField.text])
                                    }
                                }
                                EntryButton {
                                    text: root.t("guide")
                                    visible: !!card.modelData.docs && card.modelData.available
                                    quiet: true
                                    enabled: !root.busy
                                    onClicked: root.actionRequested(["docs", card.modelData.id])
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                implicitHeight: statusText.implicitHeight + 24
                radius: 9; color: "#172235"; border.color: "#2d3c55"
                Text {
                    id: statusText
                    objectName: "statusText"
                    anchors.fill: parent; anchors.margins: 12
                    text: root.busy ? root.t("working") : (root.message || root.t("welcome"))
                    textFormat: Text.PlainText
                    wrapMode: Text.WrapAnywhere
                    color: "#b7c8e5"; font.pixelSize: 12
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    text: root.t("footer")
                    color: "#7f91ad"; font.pixelSize: 11
                }
                EntryButton { text: root.t("edit_config"); quiet: true; enabled: !root.busy; onClicked: root.actionRequested(["edit-config"]) }
            }
        }
    }

    Dialog {
        id: registerDialog
        objectName: "registerDialog"
        title: root.t("register_title")
        modal: true
        anchors.centerIn: parent
        width: Math.min(root.width - 40, 570)
        standardButtons: Dialog.NoButton
        background: Rectangle { color: "#202c42"; radius: 12; border.color: "#526787" }
        header: Text { text: root.t("register_title"); color: "#f0f4ff"; font.pixelSize: 20; padding: 20 }
        contentItem: ColumnLayout {
            spacing: 12
            EntryField { id: entryId; Layout.fillWidth: true; placeholderText: root.t("entry_id") }
            EntryField { id: entryName; Layout.fillWidth: true; placeholderText: root.t("entry_name") }
            ComboBox {
                id: entryKind
                objectName: "entryKind"
                Layout.fillWidth: true
                model: ["terminal", "gui", "web"]
                displayText: root.t("kind_" + currentText)
                palette.text: "#e8eefc"
                palette.buttonText: "#e8eefc"
                palette.button: "#101827"
                palette.base: "#202c42"
                contentItem: Text {
                    text: entryKind.displayText
                    color: "#e8eefc"
                    font.pixelSize: 13
                    leftPadding: 12
                    rightPadding: 32
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle { color: "#101827"; radius: 6; border.color: "#3b4a64" }
                indicator: Text {
                    text: "▾"
                    color: "#9cabc4"
                    font.pixelSize: 18
                    x: entryKind.width - width - 12
                    anchors.verticalCenter: parent.verticalCenter
                }
                delegate: ItemDelegate {
                    required property string modelData
                    required property int index
                    width: entryKind.width
                    text: root.t("kind_" + modelData)
                    highlighted: entryKind.highlightedIndex === index
                    contentItem: Text { text: parent.text; color: "#e8eefc"; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter }
                    background: Rectangle { color: parent.highlighted ? "#33435f" : "#202c42" }
                }
            }
            EntryField {
                id: entryValue
                Layout.fillWidth: true
                placeholderText: entryKind.currentIndex === 2 ? "https://example.com/console" : root.t("command_hint")
            }
            Text {
                Layout.fillWidth: true; wrapMode: Text.WordWrap
                color: "#bdc9dc"; font.pixelSize: 12
                text: root.t("registration_note")
            }
            RowLayout {
                Item { Layout.fillWidth: true }
                EntryButton { text: root.t("cancel"); onClicked: registerDialog.close() }
                EntryButton {
                    text: root.t("save_entry"); accent: true
                    enabled: !root.busy && entryId.text.length > 0 && entryName.text.length > 0 && entryValue.text.length > 0
                    onClicked: {
                        root.actionRequested(["register", entryId.text, entryName.text, ["terminal", "gui", "web"][entryKind.currentIndex], entryValue.text])
                        registerDialog.close()
                    }
                }
            }
        }
    }
}
