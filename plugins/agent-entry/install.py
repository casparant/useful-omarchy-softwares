#!/usr/bin/env python3
"""Install this local plugin without changing system packages or overwriting user data."""

# Modified 2026-10-19: deploy bilingual resources and localized desktop menu metadata.
# Modified 2026-10-20: link the repository omarchy-tools so install entries are discoverable.
# Apache-2.0 source and revision: ORIGIN.md.

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ID = "anolisa.agent-entry"
SOURCE = Path(__file__).resolve().parent
FILES = [
    "manifest.json",
    "BarWidget.qml",
    "Dashboard.qml",
    "DashboardContent.qml",
    "AwWorkbench.qml",
    "ControlContent.qml",
    "HookPlan.qml",
    "EntryButton.qml",
    "EntryField.qml",
    "I18n.js",
    "agent_entry.py",
    "aw_status.py",
    "workspace.py",
    "cosh-shell",
    "cosh-aw.bash",
    "i18n.py",
    "install.py",
    "LICENSE",
    "NOTICE",
    "ORIGIN.md",
    "README.md",
    "README_zh.md",
]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, timeout=15)


def desktop_quote(value: str) -> str:
    if any(c in value for c in "\n\r\0"):
        raise ValueError("非法路径")
    return (
        '"'
        + value.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
        + '"'
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--autostart", action="store_true", help="每次登录后显示 Dashboard")
    p.add_argument("--replace", action="store_true", help="备份已有同名插件后升级")
    p.add_argument("--uninstall", action="store_true", help="禁用并移至备份目录；保留 Agent 与配置")
    args = p.parse_args()
    if sys.platform != "linux":
        p.error("安装器仅在目标 Linux 桌面上运行；macOS 可运行测试。")
    if os.geteuid() == 0:
        p.error("请使用登录桌面的普通用户，不要 sudo。")
    for tool in ("omarchy", "omarchy-shell", "python3"):
        if not shutil.which(tool):
            p.error("未找到 " + tool + "；请在 Omarchy 图形会话中运行。")
    config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    # Omarchy scans HOME/.config directly, independently of XDG_CONFIG_HOME.
    shell_config = Path.home() / ".config/omarchy"
    target = shell_config / "plugins" / ID
    backups = config / "anolisa/plugin-backups"
    launcher = Path.home() / ".local/bin/anolisa-agent-entry"
    desktop = Path.home() / ".local/share/applications/anolisa-agent-entry.desktop"
    workspace_link = Path.home() / ".local/bin/aw-session"
    workspace_desktop = Path.home() / ".local/share/applications/anolisa-cosh.desktop"
    autostart = shell_config / "hooks/post-boot.d/anolisa-agent-entry.sh"
    # Install entries need omarchy-tools on PATH. Derive it from this checkout instead of
    # baking a repository path into the plugin, and never take over someone else's file.
    tools_source = SOURCE.parent.parent / "omarchy-tools"
    tools_link = Path.home() / ".local/bin/omarchy-tools"

    def link_tools() -> None:
        if not tools_source.is_file():
            print("未找到 " + str(tools_source) + "；安装入口将不会显示。")
            return
        if tools_link.is_symlink():
            if tools_link.resolve() != tools_source.resolve():
                print("保留已有的 " + str(tools_link) + "；安装入口沿用该目标。")
            return
        if tools_link.exists():
            print("保留已有的 " + str(tools_link) + "；安装入口沿用该目标。")
            return
        tools_link.parent.mkdir(parents=True, exist_ok=True)
        tools_link.symlink_to(tools_source)
        print("已链接 " + str(tools_link) + " → " + str(tools_source))
    if args.replace and not args.uninstall and SOURCE.resolve() == target.resolve():
        p.error("请从新的源码或导出目录运行 --replace；不能就地替换已部署的插件目录。")
    if args.uninstall:
        run(["omarchy", "plugin", "disable", ID])
        paths = [target, launcher, desktop, autostart]
        if workspace_link.is_symlink() and workspace_link.resolve() == (target / "workspace.py").resolve():
            paths.append(workspace_link)
        if workspace_desktop.is_file() and ("Exec=" + desktop_quote(str(launcher)) + " launch cosh") in workspace_desktop.read_text():
            paths.append(workspace_desktop)
        backup = backups / ("removed-" + str(time.time_ns()))
        backup.mkdir(parents=True)
        for path in paths:
            if path.exists() or path.is_symlink():
                # These are exact, plugin-owned paths; never remove Agent software.
                shutil.move(str(path), str(backup / (path.parent.name + "-" + path.name)))
        run(["omarchy-shell", "shell", "rescanPlugins"])
        if tools_link.is_symlink() and tools_link.resolve() == tools_source.resolve():
            shutil.move(str(tools_link), str(backup / (tools_link.parent.name + "-" + tools_link.name)))
        print("插件文件已移至可恢复备份：", backup)
        print("Agent 安装、账号与 ~/.config/anolisa/agent-entry.json 均保留。")
        return
    run(["omarchy", "plugin", "validate", str(SOURCE)])
    owned_paths = [target, launcher, desktop] + ([autostart] if args.autostart else [])
    existing = [path for path in owned_paths if path.exists() or path.is_symlink()]
    if existing and not args.replace:
        p.error("已有同名安装。确认升级请加 --replace，旧文件会备份。")
    if existing:
        backup = backups / ("upgrade-" + str(time.time_ns()))
        backup.mkdir(parents=True)
        for path in existing:
            shutil.move(str(path), str(backup / (path.parent.name + "-" + path.name)))
        print("升级前备份：", backup)
    target.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / name, target / name)
    helper = target / "agent_entry.py"
    helper.chmod(0o755)
    (target / "workspace.py").chmod(0o755)
    (target / "cosh-shell").chmod(0o755)
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.symlink_to(helper)
    if workspace_link.is_symlink() and workspace_link.resolve() == (target / "workspace.py").resolve():
        workspace_link.unlink()
    if not workspace_link.exists() and not workspace_link.is_symlink():
        workspace_link.symlink_to(target / "workspace.py")
    else:
        print("保留已有 aw-session；可通过插件目录 workspace.py 使用托管命令。")
    if not workspace_desktop.exists():
        workspace_desktop.parent.mkdir(parents=True, exist_ok=True)
        workspace_desktop.write_text(
            "[Desktop Entry]\nType=Application\nName=cosh\nName[zh_CN]=cosh · AI Shell\n"
            "Exec=" + desktop_quote(str(launcher)) + " launch cosh\n"
            "Icon=utilities-terminal\nTerminal=false\nCategories=Development;Utility;\n",
            encoding="utf-8")
    desktop.parent.mkdir(parents=True, exist_ok=True)
    desktop_text = (
        "[Desktop Entry]\nType=Application\nName=Agent Entry\n"
        "Name[zh_CN]=Agent 入口\nName[zh_TW]=Agent 入口\n"
        "Comment=Launch native agents and terminals\n"
        "Comment[zh_CN]=启动原生 Agent 与终端\n"
        "Comment[zh_TW]=啟動原生 Agent 與終端\n"
        "Exec=" + desktop_quote(str(launcher)) + " open\n"
        "Icon=utilities-terminal\nTerminal=false\nCategories=Development;Utility;\n"
    )
    desktop.write_text(desktop_text, encoding="utf-8")
    if args.autostart:
        autostart.parent.mkdir(parents=True, exist_ok=True)
        autostart.write_text(
            "#!/bin/bash\n# ANOLISA Agent Entry — opt-in startup hook\n"
            + shlex.quote(str(launcher))
            + " open >/dev/null 2>&1 &\n",
            encoding="utf-8",
        )
    run(["omarchy-shell", "shell", "rescanPlugins"])
    # Discovery is asynchronous. Retry enable; do not edit shell.json directly.
    for attempt in range(15):
        outcome = subprocess.run(["omarchy", "plugin", "enable", ID], timeout=10)
        if outcome.returncode == 0:
            break
        time.sleep(0.3)
    else:
        raise RuntimeError("插件已复制，但启用失败。请查看 omarchy-shell 日志，不要重复覆盖配置。")
    run(["omarchy-shell", "shell", "summon", ID, "{}"])
    link_tools()
    print("已安装。顶栏点击 Agent 入口；也可运行 ~/.local/bin/anolisa-agent-entry open")
    if args.autostart:
        print("已写入 Omarchy post-boot.d 独立启动钩子；不修改 Hyprland 或现有钩子文件。")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print("安装未完成：" + str(error), file=sys.stderr)
        sys.exit(1)
