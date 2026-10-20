#!/usr/bin/python3
"""Initialize a private Qoder configuration once, then launch through aw run."""
import json
import os
import re
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time


PREFIX = Path("@PREFIX@")
PACKAGED_QODER = Path("/usr/bin/qodercli")
UNIT = "aw-preview-sec-core.service"
SOCKET = "/run/aw-preview-sec-core/daemon.sock"


class SetupError(Exception):
    """An actionable setup failure; existing configuration is preserved."""


def command(args, capture=True, timeout=20):
    result = subprocess.run([str(arg) for arg in args], text=True,
                            stdout=subprocess.PIPE if capture else None,
                            stderr=subprocess.PIPE if capture else None,
                            timeout=timeout)
    if result.returncode:
        raise SetupError((result.stderr or "Command failed: " + str(args[0])).strip())
    return result.stdout or ""


def private_directory(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise SetupError("Use a directory owned by you without group/other write access: " + str(path))


def paths():
    config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    if not config.is_absolute() or not state.is_absolute():
        raise SetupError("XDG_CONFIG_HOME and XDG_STATE_HOME must be absolute paths.")
    return config / "aw/preview.yaml", state / "aw-preview/runtime"


def health(socket=SOCKET, wait=False):
    directory = PREFIX / "libexec/aw/providers/sec-core"
    deadline = time.monotonic() + (5 if wait else 0)
    # systemctl's simple service start precedes socket readiness. Only explicit
    # initial activation waits; daily checks never restart or retry a backend.
    for _ in range(26):
        value = json.loads(command([directory / "aw-provider-sec-core", "--health", "--helper",
                                    directory / "agent-sec-daemon-health", "--socket", socket], timeout=2))
        if value.get("backend") == "authenticated_reachable":
            return
        remaining = deadline - time.monotonic()
        if not wait or remaining <= 0:
            break
        time.sleep(min(0.2, remaining))
    raise SetupError("Security backend is unavailable. AW will not start without the selected "
                     "security checks. Restore the backend before reopening AW.")


def initialize(config, state):
    print("AW first-time setup\nCompression is enabled with Tokenless. Your agent keeps its own permissions.")
    packaged = PACKAGED_QODER
    candidate = str(packaged) if packaged.is_file() and os.access(packaged, os.X_OK) else shutil.which("qodercli") or ""
    # Desktop session PATH can omit user-installed Qoder even when it is present.
    local = Path.home() / ".local/bin/qodercli"
    if not candidate and local.is_file() and os.access(local, os.X_OK):
        candidate = str(local)
    selected = input("Qoder CLI absolute path" + (" [" + candidate + "]" if candidate else "") + ": ").strip()
    qoder = Path(selected or candidate)
    if not qoder.is_absolute() or not qoder.is_file() or not os.access(qoder, os.X_OK):
        raise SetupError("Install qodercli-bin or select an executable Qoder CLI, then reopen AW.")
    version = command([qoder, "--version"]).strip()
    match = re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", version)
    if not match or tuple(map(int, match.groups()[:3])) < (1, 1, 64) or (match.groups()[:3] == ("1", "1", "64") and match.group(4)):
        raise SetupError("Qoder CLI >= 1.1.64 is required. Upgrade your agent, then reopen AW.")
    print("Qoder CLI " + version)
    choice = input("Enable security checks with sec-core? This may request system authorization [y/N]: ").strip().lower()
    if choice not in ("", "n", "no", "y", "yes"):
        raise SetupError("Choose yes or no. No AW configuration was written.")
    security = choice in ("y", "yes")
    private_directory(config.parent)
    private_directory(state.parent)
    if security:
        print("Enabling the dedicated AW security service. Existing security services are not changed.")
        command(["/usr/bin/sudo", "/usr/bin/systemctl", "enable", "--now", UNIT],
                capture=False, timeout=300)
        health(wait=True)
    args = [PREFIX / "bin/aw-package", "configure", "--prefix", PREFIX,
            "--config", config, "--state-dir", state, "--qoder", qoder,
            "--provider", "sec-core+tokenless" if security else "tokenless"]
    if security:
        args += ["--socket", SOCKET]
    command(args)
    print("AW configuration saved. Future launches reuse it.")


def prepare():
    if os.getuid() == 0:
        raise SetupError("Open AW as your desktop user, not root.")
    config, state = paths()
    if not config.exists() and not config.is_symlink():
        initialize(config, state)
    # The upstream editor validates ownership, links and permissions without
    # rewriting existing policy or user Hook steps.
    document = json.loads(command([PREFIX / "bin/aw-package", "config", "show", "--config", config]))
    agent = document["spec"]["agents"].get("qoder")
    if not agent or agent.get("adapter") != "qoder":
        raise SetupError("This desktop entry requires a qoder target. Use aw run for other targets.")
    command([PREFIX / "bin/aw", "validate", "--config", config])
    security = document["spec"]["providers"].get("security", {})
    argv = security.get("transport", {}).get("argv", [])
    if argv and argv[0] == str(PREFIX / "libexec/aw/providers/sec-core/aw-provider-sec-core"):
        # Reuse the explicitly configured backend; never start it on daily launch.
        if "--socket" not in argv or len(argv[argv.index("--socket") + 1:]) != 1:
            raise SetupError("The security socket configuration is incomplete.")
        socket = argv[argv.index("--socket") + 1]
        if not Path(socket).is_absolute():
            raise SetupError("The security socket must be an absolute path.")
        health(socket)
    qoder = agent["argv"][0]
    if not os.environ.get("QODER_PERSONAL_ACCESS_TOKEN"):
        status = command([qoder, "status"])
        if "Not logged in" in status:
            print("Qoder sign-in is required. The native login flow manages your credentials.")
            if input("Open Qoder login now? [Y/n]: ").strip().lower() not in ("", "y", "yes"):
                raise SetupError("Sign-in cancelled. Your AW configuration was kept.")
            command([qoder, "login"], capture=False, timeout=300)
            if "Not logged in" in command([qoder, "status"]):
                raise SetupError("Qoder is not signed in. Reopen AW after completing native login.")
    return [str(PREFIX / "bin/aw"), "run", "--config", str(config), "--agent", "qoder"]


def main():
    try:
        native = sys.argv[1:]
        if native and native[0] != "--":
            raise SetupError("Pass native Qoder arguments after --.")
        args = prepare() + native
        os.execv(args[0], args)
    except (EOFError, KeyboardInterrupt):
        print("AW setup cancelled. Existing configuration was kept.", file=sys.stderr)
        return 130
    except (SetupError, OSError, ValueError, KeyError, IndexError, subprocess.TimeoutExpired) as error:
        print("AW: " + str(error), file=sys.stderr)
        if sys.stdin.isatty():
            try:
                input("Press Enter to close. ")
            except (EOFError, KeyboardInterrupt):
                pass
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
