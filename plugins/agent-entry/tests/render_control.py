"""QtQuick PoC acceptance with explicit fixtures; does not start applications."""

import importlib.util
import json
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine, QQmlExpression
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
fixture["recent_execution"]["data"]["items"] = [
    {"provider": "security", "step_id": "scan-code", "status": "ok",
     "policy_block": True, "failure_action": None, "elapsed_ms": 1},
    {"provider": "tokenless-main", "step_id": "rewrite-command", "status": "ok",
     "policy_block": True, "failure_action": None, "elapsed_ms": 2},
    {"provider": "security", "step_id": "scan-code", "status": "ok",
     "policy_block": False, "failure_action": None, "elapsed_ms": 3},
]
report = test.aw.project(fixture, "security")
report["hook_plan"] = test.aw.hook_plan(test.configuration(), "security", "tokenless")
report["security"] = {"backend": "authenticated_reachable"}
root.setProperty("aw", report)
root.setProperty("runtime", {"state": "online", "updated": "12:06:18", "sessions": [
    {"id": "a" * 32, "agent": "Qoder", "state": "blocked", "project": "/home/demo/project",
     "policy": "bound", "revision": "a5f7dda46807", "pid": 1234, "pane": "w2:p1",
     "conversation": "demo-conversation", "tokenless": {"enabled": True}, "security": {"enabled": True, "backend": "authenticated_reachable"}, "hook_plan": report["hook_plan"], "activities": report["activities"]},
    {"id": "", "agent": "Qoder", "state": "unknown", "project": "/home/demo/other",
     "policy": "unmanaged", "pid": 2345, "pane": ""},
]})

for role, expected in [("security", ["security_block", "security_checked"]),
                       ("tokenless", ["optimization_retry"])]:
    expression = QQmlExpression(QQmlEngine.contextForObject(root), root,
                               f'JSON.stringify(componentActivities("{role}"))')
    value, undefined = expression.evaluate()
    assert not expression.hasError() and not undefined
    assert [item["kind"] for item in json.loads(value)] == expected, (role, value)


def find(name):
    item = root.findChild(QObject, name)
    if item is None:
        pending = list(root.childItems())
        while pending:
            child = pending.pop()
            if child.objectName() == name:
                item = child
                break
            pending.extend(child.childItems())
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
    assert 0 <= point.x() < view.width() and 0 <= point.y() < view.height(), (name, view.width(), view.height(), point)
    QTest.mouseClick(view, Qt.LeftButton, Qt.NoModifier, QPoint(round(point.x()), round(point.y())))
    QTest.qWait(100)


view.show()
for language in ["en", "zh"]:
    root.setProperty("language", language)
    for compact, width, height in [(True, 460, 920), (True, 360, 640), (False, 880, 900)]:
        root.setProperty("compact", compact)
        view.resize(width, height)
        QTest.qWait(150)
        click("controlCoshCompact" if compact else "controlCosh")
        assert actions.pop() == ["launch", "cosh", "--project", "/home/demo/project"]
        if not compact:
            click("sessionDetails-" + "a" * 32)
            assert find("session-" + "a" * 32).property("expanded")
            refreshed = root.property("runtime").toVariant()
            refreshed["updated"] = "12:06:19"
            root.setProperty("runtime", refreshed)
            QTest.qWait(150)
            assert find("session-" + "a" * 32).property("expanded")
            click("sessionDetails-" + "a" * 32)
        if compact:
            footer = find("controlCoshCompact")
            footer_position = footer.mapToScene(footer.boundingRect().center())
            area = find("controlScroll").property("contentItem")
            area.setProperty("contentY", max(0, area.property("contentHeight") - area.property("height")))
            QTest.qWait(100)
            assert footer.mapToScene(footer.boundingRect().center()) == footer_position
            assert 0 < footer_position.y() < view.height()
            assert not root.property("tokenExpanded")
            click("controlTokenToggle")
            assert root.property("tokenExpanded"), (language, width, height, "token expand")
            click("controlSecurityToggle")
            assert root.property("securityExpanded")
            click("controlPolicyToggle")
            assert root.property("policyExpanded")
            click("controlTokenToggle")
            click("controlSecurityToggle")
            click("controlPolicyToggle")
            click("controlDetails")
            assert detail_requests and not actions
        find("controlScroll").property("contentItem").setProperty("contentY", 0)
        QTest.qWait(100)
        assert view.grabWindow().save(str(output / f"control-{language}-{width}.png"))
assert "a5f7dda468" in find("compactHooks").property("evidence")
root.setProperty("runtime", {"state": "unavailable", "sessions": []})
QTest.qWait(100)
assert "a5f7dda468" not in find("compactHooks").property("evidence")
assert not root.property("boundSessions").toVariant()
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
