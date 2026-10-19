# Modified 2026-10-19: bilingual layout, language action and form-state regression checks.
# Apache-2.0; see ../LICENSE, ../NOTICE and ../ORIGIN.md.
"""Optional real QtQuick layout test. Requires PySide6, not needed by the plugin."""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, Qt, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QJSEngine
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("entry", ROOT / "agent_entry.py")
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
# Never read real user settings or credentials while rendering fixtures.
temporary = tempfile.TemporaryDirectory()
entry.config_path = lambda: Path(temporary.name) / "agent-entry.json"
app = QGuiApplication(sys.argv)
engine = QJSEngine()
source = (ROOT / "I18n.js").read_text().replace(".pragma library", "")
result = engine.evaluate(source)
assert not result.isError(), result.toString()
keys = engine.evaluate("JSON.stringify([Object.keys(strings.en).sort(), Object.keys(strings.zh).sort()])")
en_keys, zh_keys = json.loads(keys.toString())
assert en_keys == zh_keys, "UI translation keys must match in both languages"
view = QQuickView()
view.setResizeMode(QQuickView.SizeRootObjectToView)
view.setSource(QUrl.fromLocalFile(str(ROOT / "DashboardContent.qml")))
if view.status() == QQuickView.Error:
    raise SystemExit("\n".join(e.toString() for e in view.errors()))
root = view.rootObject()
root.setProperty("project", "/home/user/Projects/example")
view.setTitle("Agent Entry — bilingual layout QA")
view.resize(1160, 740)
view.show()
output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/agent-entry-preview.png")
actions = []
root.actionRequested.connect(
    lambda value: actions.append(value.toVariant() if hasattr(value, "toVariant") else value)
)


def find(name: str):
    item = root.findChild(QObject, name)
    pending = [root]
    while item is None and pending:
        candidate = pending.pop()
        if candidate.objectName() == name:
            item = candidate
        else:
            pending.extend(candidate.childItems())
    if item is None:
        raise RuntimeError("Missing UI item: " + name)
    return item


def flickable():
    return find("dashboardScroll").property("contentItem")


def scroll_to_bottom():
    area = flickable()
    area.setProperty("contentY", max(0, area.property("contentHeight") - area.property("height")))
    QTest.qWait(100)


def click(name: str):
    item = find(name)
    point = item.mapToScene(item.boundingRect().center())
    assert 0 <= point.y() <= view.height(), (name, point, view.size())
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, QPoint(round(point.x()), round(point.y())))
    QTest.qWait(80)


def set_language(language: str):
    entry.save_config({"version": 1, "language": language, "agents": []})
    items = entry.catalog()
    for item in items:
        item["available"] = False
        item["status"] = entry.tr("尚未发现启动入口", "Launcher not found")
    root.setProperty("language", language)
    root.setProperty("agents", items)
    root.setProperty("message", "")
    QTest.qWait(100)


def save(suffix: str = ""):
    path = output.with_name(output.stem + suffix + output.suffix)
    assert view.grabWindow().save(str(path)), "Failed to capture " + str(path)
    print(path)


def capture():
    try:
        set_language("en")
        assert find("heading").property("text") == "Start your next agent session"
        assert find("statusText").property("text").startswith("Choose an agent")
        click("openTerminal")
        assert actions[-1] == ["launch", "terminal", "--project", "/home/user/Projects/example"], actions
        click("agentAction-qoder")
        assert actions[-1] == ["docs", "qoder", "--project", "/home/user/Projects/example"], actions
        save()
        click("addEntry")
        dialog = find("registerDialog")
        assert dialog.property("visible"), "Registration dialog did not open"
        assert dialog.property("title") == "Add an agent entry"
        kind = find("entryKind")
        kind.setProperty("currentIndex", 2)
        draft = "/home/demo/Projects/unsaved-folder"
        find("projectField").setProperty("text", draft)
        save("-register-en")
        click("entryKind")
        QTest.qWait(100)
        save("-register-options-en")
        QTest.keyClick(view, Qt.Key_Escape)
        QTest.qWait(80)
        assert dialog.property("visible"), "Closing the type menu must keep the dialog open"
        assert kind.property("currentIndex") == 2
        # A live language change must preserve the Web type and unsaved form fields.
        set_language("zh")
        assert dialog.property("title") == "添加 Agent 入口"
        assert kind.property("currentIndex") == 2
        assert kind.property("displayText") == "Web 页面"
        assert find("projectField").property("text") == draft
        save("-register-zh")
        QTest.keyClick(view, Qt.Key_Escape)
        QTest.qWait(80)
        assert not dialog.property("visible"), "Escape did not close dialog"
        assert find("heading").property("text") == "从这里，开始 Agent 工作"
        save("-zh")
        root.setProperty("busy", True)
        assert find("statusText").property("text") == "正在处理…"
        root.setProperty("language", "en")
        assert find("statusText").property("text") == "Working…"
        root.setProperty("busy", False)
        set_language("en")
        flickable().setProperty("contentY", 0)
        QTest.qWait(150)
        click("languageToggle")
        assert actions[-1] == ["language", "zh"], actions
        set_language("zh")  # Apply the helper response without running an external process.
        QTest.qWait(400)
        click("languageToggle")
        assert actions[-1] == ["language", "en"], actions
        set_language("en")
        view.resize(800, 680)
        QTest.qWait(150)
        flickable().setProperty("contentY", 0)
        QTest.qWait(100)
        save("-narrow-en")
        area = flickable()
        assert area.property("contentHeight") > area.property("height"), "Narrow layout must scroll"
        scroll_to_bottom()
        click("agentAction-qoderwake")
        assert actions[-1] == ["docs", "qoderwake", "--project", draft], actions
        save("-narrow-bottom-en")
        set_language("zh")
        flickable().setProperty("contentY", 0)
        QTest.qWait(100)
        save("-narrow-zh")
        print("PASS: en/zh rendering, translated busy state, language signals, preserved form state, terminal/guidance, dialog/Escape and narrow scrolling")
    except Exception:
        import traceback
        traceback.print_exc()
        app.exit(1)
        return
    app.quit()


QTimer.singleShot(1200, capture)
QTimer.singleShot(20000, lambda: app.exit(1))
code = app.exec()
temporary.cleanup()
raise SystemExit(code)
