"""QtQuick PoC acceptance with explicit fixtures; does not start applications."""

import importlib.util
import json
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("control_test", ROOT / "tests/test_control_plane.py")
test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test)
app = QGuiApplication(sys.argv)
view = QQuickView()
view.setResizeMode(QQuickView.SizeRootObjectToView)
view.setSource(QUrl.fromLocalFile(str(ROOT / "ControlContent.qml")))
assert view.status() != QQuickView.Error, view.errors()
root = view.rootObject()
output = Path(sys.argv[1])
output.mkdir(parents=True, exist_ok=True)
actions, detail_requests, closed = [], [], []
root.actionRequested.connect(lambda v: actions.append(v.toVariant()))
root.detailsRequested.connect(lambda: detail_requests.append(True))
root.closeRequested.connect(lambda: closed.append(True))
root.setProperty("project", "/home/demo/project")
root.setProperty("agents", [{"id": "cosh", "available": True}])
fixture = json.loads((ROOT / "tests/fixtures/panel-ok.json").read_text())
report = test.aw.project(fixture)
report["hook_plan"] = test.aw.hook_plan(test.configuration(), "security", "tokenless")
report["security"] = {"backend": "authenticated_reachable"}
root.setProperty("aw", report)
root.setProperty("runtime", {"state": "online", "updated": "12:06:18", "sessions": [
    {"id": "a" * 32, "agent": "Qoder", "state": "blocked", "project": "/home/demo/project",
     "policy": "bound", "revision": "a5f7dda46807", "pid": 1234, "pane": "w2:p1",
     "conversation": "demo-conversation", "tokenless": {"enabled": True}, "security": {"enabled": True, "backend": "authenticated_reachable"}, "hook_plan": report["hook_plan"]},
    {"id": "", "agent": "Qoder", "state": "unknown", "project": "/home/demo/other",
     "policy": "unmanaged", "pid": 2345, "pane": ""},
]})


def find(name):
    item = root.findChild(QObject, name)
    assert item is not None, name
    return item


def click(name):
    item = find(name)
    area = find("controlScroll").property("contentItem")
    point = item.mapToScene(item.boundingRect().center())
    area.setProperty("contentY", max(0, min(area.property("contentHeight") - area.property("height"),
                                          area.property("contentY") + point.y() - view.height() / 2)))
    QTest.qWait(100)
    point = item.mapToScene(item.boundingRect().center())
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, QPoint(round(point.x()), round(point.y())))
    QTest.qWait(100)


view.show()
for language in ["en", "zh"]:
    root.setProperty("language", language)
    for compact, width, height in [(True, 460, 920), (True, 360, 640), (False, 880, 900)]:
        root.setProperty("compact", compact)
        view.resize(width, height)
        QTest.qWait(150)
        click("controlCosh")
        assert actions.pop() == ["launch", "cosh", "--project", "/home/demo/project"]
        if compact:
            click("controlDetails")
            assert detail_requests and not actions
        find("controlScroll").property("contentItem").setProperty("contentY", 0)
        QTest.qWait(100)
        assert view.grabWindow().save(str(output / f"control-{language}-{width}.png"))
root.setProperty("aw", test.aw.empty("query_failed"))
QTest.qWait(100)
assert find("controlSavings").property("text") == "—"
assert find("controlHooks").property("plan").toVariant()["phases"] == []
root.setProperty("aw", report)
root.setProperty("busy", True)
QTest.qWait(100)
assert not find("controlCosh").property("enabled")
assert not find("controlRefresh").property("enabled")
root.setProperty("busy", False)
QTest.keyClick(view, Qt.Key_Escape)
assert closed
view.close()
print("Workbench: bilingual compact/detail, narrow layout, cosh action, bound/unmanaged sessions, stale data and Escape passed")
