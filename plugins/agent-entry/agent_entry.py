#!/usr/bin/env python3
"""Local Agent launcher and package guidance. No software installer."""

# Modified 2026-10-19: persistent Chinese/English preferences and localized launcher output.
# Modified 2026-10-20: focus an already-running GUI window instead of re-spawning into its own lock.
# Original Apache-2.0 source and revision are recorded in ORIGIN.md.

from __future__ import annotations

import argparse
import copy
import json
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PLUGIN_ID = "anolisa.agent-entry"

# Load the sibling module by path: standalone exports and spec-based tests do not
# require modifying sys.path or importing an unrelated globally installed i18n.
_i18n_spec = importlib.util.spec_from_file_location("agent_entry_i18n", ROOT / "i18n.py")
_i18n = importlib.util.module_from_spec(_i18n_spec)
_i18n_spec.loader.exec_module(_i18n)

_aw_spec = importlib.util.spec_from_file_location("agent_entry_aw_status", ROOT / "aw_status.py")
_aw = importlib.util.module_from_spec(_aw_spec)
_aw_spec.loader.exec_module(_aw)


def language_settings() -> dict[str, str]:
    """Read only the optional language field; never recurse through config errors."""
    preference = "auto"
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("language", "auto") in _i18n.PREFERENCES:
            preference = data.get("language", "auto")
    except (OSError, ValueError):
        pass
    return {"language": _i18n.resolve_language(preference), "languagePreference": preference}


def tr(zh: str, en: str) -> str:
    return _i18n.translate(zh, en, language_settings()["language"])


def config_path() -> Path:
    return (
        Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        / "anolisa/agent-entry.json"
    )


def env() -> dict[str, str]:
    result = os.environ.copy()
    paths = [
        str(Path.home() / p)
        for p in (
            ".local/bin",
            ".local/share/mise/shims",
        )
    ]
    # The prototype installed Codex here. Keep discovery as a final fallback;
    # current PATH installations take precedence and no installer remains.
    legacy_codex = str(Path.home() / ".local/share/anolisa/agent-entry/npm/bin")
    result["PATH"] = os.pathsep.join(paths + [result.get("PATH", ""), legacy_codex])
    return result


def which(command: str) -> str | None:
    return shutil.which(os.path.expanduser(command), path=env()["PATH"])


def catalog() -> list[dict[str, Any]]:
    return [
        dict(
            id="aw",
            name="AW",
            kind="terminal",
            candidates=["/usr/bin/aw-launch"],
            subtitle=tr("Tokenless 压缩 · 可选安全检查", "Tokenless compression · optional security"),
            docs="https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/aw-preview/README.md",
        ),
        dict(
            id="cosh",
            name="cosh-ng",
            kind="terminal",
            candidates=["cosh-ng", "cosh"],
            subtitle=tr("ANOLISA 交互终端", "Interactive terminal"),
            docs="https://github.com/casparant/ANOLISA",
        ),
        dict(
            id="qoder",
            name="Qoder",
            kind="gui",
            candidates=["qoder-desktop", "Qoder"],
            subtitle=tr("图形客户端 · 独立 Arch 配方", "Desktop app · Arch package recipe"),
            docs="https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qoder-bin/README.md",
        ),
        dict(
            id="qoder-ide",
            name="Qoder IDE",
            kind="gui",
            candidates=["qoder-ide", "QoderIDE"],
            subtitle=tr("代码编辑器 · 独立 Arch 配方", "Code editor · Arch package recipe"),
            docs="https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qoder-ide-bin/README.md",
        ),
        dict(
            id="qoder-cli",
            name="Qoder CLI",
            kind="terminal",
            candidates=["qodercli"],
            subtitle=tr("直接启动，不经过 AW", "Direct launch, without AW"),
            docs="https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qodercli-bin/README.md",
        ),
        dict(
            id="codex",
            name="Codex CLI",
            kind="terminal",
            candidates=["codex"],
            subtitle=tr("终端版 · 非桌面客户端", "Command-line agent"),
            docs="https://github.com/openai/codex",
        ),
        dict(
            id="qoderwake",
            name="QoderWake",
            kind="wake",
            candidates=["qoderwake"],
            subtitle=tr("Linux 服务 + Web Console", "Linux service + web console"),
            docs="https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/qoderwake-bin/README.md",
        ),
    ]


def valid_argv(value: object) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > 64:
        raise ValueError(tr('启动命令必须是非空 JSON 字符串数组，例如 ["cosh-ng"]', "The launch command must be a nonempty JSON array of strings, e.g. [\"cosh-ng\"]"))
    if any(not isinstance(v, str) or not v or "\0" in v or "\n" in v or "\r" in v for v in value):
        raise ValueError(tr("命令参数不能包含空值、换行或 NUL", "Command arguments cannot be empty or contain newlines or NUL"))
    return value


def valid_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme not in ("https", "http")
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError(tr("仅接受不含用户名/密码的 http(s) URL", "Use an http(s) URL without a username or password"))
    if any(c in value for c in ("\n", "\r", "\0")):
        raise ValueError(tr("URL 包含非法字符", "The URL contains an invalid character"))
    return value


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {"version": 1, "project": str(Path.home()), "agents": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(tr("配置不是有效 JSON：", "Invalid JSON configuration: ") + str(error)) from error
    if (
        not isinstance(data, dict)
        or data.get("version") != 1
        or not isinstance(data.get("agents", []), list)
    ):
        raise ValueError(tr("配置格式错误；请检查 ", "Invalid configuration; check ") + str(path))
    if data.get("language", "auto") not in _i18n.PREFERENCES:
        raise ValueError(tr("language 必须是 auto、en 或 zh", "language must be auto, en or zh"))
    return data


def save_config(data: dict[str, Any]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".agent-entry-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def project_dir(value: str | None) -> Path:
    path = Path(value or load_config().get("project", str(Path.home()))).expanduser().resolve()
    if not path.is_dir():
        raise ValueError(tr("项目目录不存在：", "Project folder does not exist: ") + str(path))
    return path


def agents() -> list[dict[str, Any]]:
    items = catalog()
    seen = {a["id"] for a in items}
    for item in load_config().get("agents", []):
        if not isinstance(item, dict) or not re.fullmatch(
            r"local\.[a-z0-9_-]+", item.get("id", "")
        ):
            raise ValueError(tr("自定义入口 id 必须使用 local. 前缀", "Custom entry IDs must start with local."))
        if item["id"] in seen:
            raise ValueError(tr("重复的入口 id：", "Duplicate entry ID: ") + item["id"])
        if item.get("kind") not in ("terminal", "gui", "web"):
            raise ValueError(tr("未知入口类型", "Unknown entry type"))
        if item["kind"] == "web":
            valid_url(item.get("url", ""))
        else:
            valid_argv(item.get("argv"))
        items.append(
            dict(item, subtitle=item.get("subtitle", tr("自定义入口", "Custom entry")), docs="")
        )
        seen.add(item["id"])
    overrides = load_config().get("commands", {})
    if not isinstance(overrides, dict):
        raise ValueError(tr("commands 必须是对象", "commands must be an object"))
    for item in items:
        if item["id"] in overrides:
            item["argv"] = valid_argv(overrides[item["id"]])
    return items


def get_agent(agent_id: str) -> dict[str, Any]:
    for item in agents():
        if item["id"] == agent_id:
            return item
    raise ValueError(tr("未知 Agent：", "Unknown agent: ") + agent_id)


def command_for(item: dict[str, Any]) -> list[str] | None:
    if "argv" in item:
        argv = valid_argv(item["argv"])
        executable = which(argv[0])
        return [executable] + argv[1:] if executable else None
    # GUI/CLI names can collide: use the desktop file to launch Qoder GUI.
    desktop_ids = {
        "qoder": ("qoder", "qoder-desktop"),
        "qoder-ide": ("qoder-ide", "qoderide"),
    }
    if item["id"] in desktop_ids and which("gtk-launch"):
        for directory in desktop_dirs():
            for file in sorted(directory.glob("*.desktop")):
                if file.stem.lower() in desktop_ids[item["id"]]:
                    return [which("gtk-launch"), file.stem]
    for candidate in item.get("candidates", []):
        executable = which(candidate)
        if executable:
            return [executable]
    return None


def snapshot() -> dict[str, Any]:
    output = []
    for source in agents():
        item = copy.deepcopy(source)
        found = command_for(item)
        ready = item["kind"] == "web" or bool(found)
        item.update(
            available=ready,
            status=(
                tr("Web 入口已配置", "Web entry configured")
                if item["kind"] == "web"
                else tr("启动入口已发现", "Ready to launch") if ready else tr("尚未发现启动入口", "Launcher not found")
            ),
        )
        # Presence can be a mise lazy launcher; it is not proof of auth or installation.
        output.append(item)
    return {
        **language_settings(),
        "agents": output,
        "aw": _aw.snapshot() if "argv" not in get_agent("aw") else _aw.empty("unsupported_launcher"),
        "project": str(project_dir(None)),
        "config": str(config_path()),
        "note": tr("检测只确认启动入口，不读取凭据，也不代表已经登录或任务正在运行。", "Detection checks launchers only. It does not read credentials or confirm sign-in or running tasks."),
    }


def detach(argv: list[str], cwd: Path | None = None) -> None:
    subprocess.Popen(
        argv,
        cwd=cwd,
        env=env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )


def terminal_argv(payload: list[str], cwd: Path) -> list[str]:
    for name in ("foot", "kitty", "alacritty", "xterm"):
        binary = which(name)
        if not binary:
            continue
        if name == "foot":
            return [
                binary,
                "--app-id=anolisa-agent-terminal",
                "--title=ANOLISA · Terminal",
                "--working-directory=" + str(cwd),
                "-e",
            ] + payload
        if name == "kitty":
            return [
                binary,
                "--class=anolisa-agent-terminal",
                "--title=ANOLISA · Terminal",
                "--directory=" + str(cwd),
            ] + payload
        if name == "alacritty":
            return [binary, "--working-directory", str(cwd), "-e"] + payload
        return [binary, "-title", "ANOLISA · Terminal", "-e"] + payload
    raise ValueError(tr("没有找到 foot / kitty / alacritty / xterm 终端", "No supported terminal found (foot / kitty / alacritty / xterm)"))


def open_terminal(payload: list[str], cwd: Path) -> None:
    detach(terminal_argv(payload, cwd), cwd)


def helper_payload(*args: str) -> list[str]:
    return [sys.executable, str(ROOT / "agent_entry.py")] + list(args)


def open_url(url: str) -> None:
    valid_url(url)
    opener = which("xdg-open")
    if not opener:
        raise ValueError(tr("没有找到 xdg-open", "xdg-open was not found"))
    detach([opener, url])


def desktop_dirs() -> list[Path]:
    """Desktop file roots, user first. A function so tests can stay off the real system dir."""
    return [Path.home() / ".local/share/applications", Path("/usr/share/applications")]


def desktop_window_class(argv: list[str]) -> str | None:
    """Anchored window-class pattern read from the desktop file this argv opens."""
    if len(argv) < 2 or Path(argv[0]).name != "gtk-launch":
        return None
    stem = argv[1]
    for directory in desktop_dirs():
        path = directory / (stem + ".desktop")
        if not path.is_file():
            continue
        value = stem
        try:
            with path.open(encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    if line.startswith("StartupWMClass="):
                        value = line.split("=", 1)[1].strip() or stem
                        break
        except OSError:
            return None
        # Unanchored, "qoder" would also match a "qoder-ide" window.
        return "^" + re.escape(value) + "$"
    return None


def focus_running(pattern: str) -> bool:
    """Bring a running window forward; False when the app or helper is absent."""
    runner = which("omarchy")
    if not runner:
        return False
    try:
        result = subprocess.run(
            [runner, "hyprland", "focus", "app", pattern], capture_output=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def launch(agent_id: str, directory: str | None = None) -> str:
    cwd = project_dir(directory)
    if agent_id == "terminal":
        shell = os.environ.get("SHELL", "/bin/bash")
        if not Path(shell).is_file():
            shell = "/bin/bash"
        open_terminal([shell], cwd)
        return tr("已请求打开终端", "Terminal launch requested")
    item = get_agent(agent_id)
    if item["kind"] == "web":
        open_url(item["url"])
        return tr("已请求打开 Web 入口", "Web entry launch requested")
    argv = command_for(item)
    if not argv:
        raise ValueError(item["name"] + tr(" 尚未发现启动入口，请安装或注册命令。", " has no launcher. Install the app or register its command."))
    if item["kind"] in ("terminal", "wake"):
        open_terminal(helper_payload("session", agent_id, "--project", str(cwd)), cwd)
    else:
        # A re-spawn hits the app's single-instance lock and exits without moving any window.
        pattern = desktop_window_class(argv)
        if pattern and focus_running(pattern):
            return item["name"] + tr(" 已在运行，窗口已切到前台。", " is already running; its window was brought forward.")
        detach(argv, cwd)
    return tr("已发起启动请求；登录与实际运行请在原生界面确认。", "Launch requested. Complete sign-in and check the session in the app.")


def session(agent_id: str, directory: str | None) -> None:
    item = get_agent(agent_id)
    argv = command_for(item)
    if not argv:
        raise ValueError(tr("启动命令不存在", "The launch command was not found"))
    cwd = project_dir(directory)
    print("ANOLISA · " + item["name"] + tr("\n工作目录：", "\nProject folder: ") + str(cwd), flush=True)
    if item["kind"] == "wake":
        # Explicit action; no public listener, no login token reads, no stored credentials.
        if subprocess.run(argv + ["whoami"], cwd=cwd, env=env()).returncode != 0:
            if subprocess.run(argv + ["login"], cwd=cwd, env=env()).returncode != 0:
                raise ValueError(tr("QoderWake 登录未完成", "QoderWake sign-in was not completed"))
        subprocess.run(
            argv + ["start", "--host", "127.0.0.1", "--open"], cwd=cwd, env=env(), check=True
        )
    else:
        # Do not append unattended / YOLO / bypass-permissions options.
        subprocess.run(argv, cwd=cwd, env=env(), check=True)


def register(args: argparse.Namespace) -> str:
    if not re.fullmatch(r"[a-z0-9_-]{1,48}", args.id):
        raise ValueError(tr("id 只允许小写字母、数字、下划线和短横线", "IDs may contain lowercase letters, digits, underscores and hyphens only"))
    name = args.name.strip()
    if not name or len(name) > 80 or any(ord(c) < 32 for c in name):
        raise ValueError(tr("名称不能为空，最多 80 字符", "The name must contain between 1 and 80 characters"))
    item = {"id": "local." + args.id, "name": name, "kind": args.kind}
    if args.kind == "web":
        item["url"] = valid_url(args.value)
    else:
        item["argv"] = valid_argv(json.loads(args.value))
    data = load_config()
    if any(x.get("id") == item["id"] for x in data.get("agents", [])):
        raise ValueError(tr("入口 id 已存在，请使用其他 id 或编辑配置", "That entry ID already exists. Choose another ID or edit the configuration."))
    data.setdefault("agents", []).append(item)
    save_config(data)
    return tr("入口已注册；启动时使用原生 Agent，不保存登录凭据。", "Entry saved. It opens the native app and does not store sign-in credentials.")


def wait_for_shell(action: str = "summon") -> str:
    binary = which("omarchy-shell")
    if not binary:
        raise ValueError(tr("未找到 omarchy-shell", "omarchy-shell was not found"))
    for _ in range(30):
        result = subprocess.run(
            [binary, "shell", "ping"], capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and "ok" in result.stdout:
            subprocess.run([binary, "shell", action, PLUGIN_ID, "{}"], check=True, timeout=5)
            return tr("入口已打开", "Agent Entry opened")
        time.sleep(1)
    raise ValueError(tr("Omarchy Shell 尚未就绪，稍后运行 agent-entry open 重试", "Omarchy Shell is not ready. Try anolisa-agent-entry open again shortly."))


def main() -> int:
    parser = argparse.ArgumentParser(description=tr("本地 Agent 启动器与安装说明，不安装软件。", "Local agent launcher and package guidance. Does not install software."))
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    sub.add_parser("open")
    sub.add_parser("toggle")
    sub.add_parser("edit-config")
    for action in ("launch", "session", "docs"):
        p = sub.add_parser(action)
        p.add_argument("id")
        p.add_argument("--project")
    p = sub.add_parser("project")
    p.add_argument("directory")
    p = sub.add_parser("language")
    p.add_argument("preference", choices=_i18n.PREFERENCES)
    p = sub.add_parser("register")
    p.add_argument("id")
    p.add_argument("name")
    p.add_argument("kind", choices=("terminal", "gui", "web"))
    p.add_argument("value", help='JSON argv, e.g. ["cosh-ng"], or a web URL')
    args = parser.parse_args()
    in_terminal = args.action == "session"
    try:
        if args.action == "status":
            result = snapshot()
        elif args.action in ("open", "toggle"):
            result = {"message": wait_for_shell("summon" if args.action == "open" else "toggle")}
        elif args.action == "launch":
            result = {"message": launch(args.id, args.project)}
        elif args.action == "session":
            session(args.id, args.project)
            result = {"message": tr("会话已结束", "Session ended")}
        elif args.action == "docs":
            open_url(get_agent(args.id)["docs"])
            result = {"message": tr("已打开安装与使用说明", "Installation and usage guide opened")}
        elif args.action == "project":
            data = load_config()
            data["project"] = str(project_dir(args.directory))
            save_config(data)
            result = {"message": tr("项目目录已保存", "Project folder saved"), "project": data["project"]}
        elif args.action == "language":
            data = load_config()
            data["language"] = args.preference
            save_config(data)
            result = {"message": tr("语言偏好已保存", "Language preference saved")}
        elif args.action == "register":
            result = {"message": register(args)}
        else:
            data = load_config()
            if not config_path().exists():
                save_config(data)
            editor = shlex.split(os.environ.get("EDITOR", "nano"))
            valid_argv(editor)
            open_terminal(editor + [str(config_path())], project_dir(None))
            result = {"message": tr("已打开配置编辑器", "Configuration editor opened")}
        result.update(language_settings())
        print(json.dumps(result, ensure_ascii=False), flush=True)
        code = 0
    except (ValueError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print(json.dumps({"error": str(error), **language_settings()}, ensure_ascii=False), flush=True)
        code = 1
    if in_terminal and sys.stdin.isatty():
        try:
            input(tr("\n按 Enter 关闭此终端。", "\nPress Enter to close this terminal."))
        except EOFError:
            pass
    return code


if __name__ == "__main__":
    sys.exit(main())
