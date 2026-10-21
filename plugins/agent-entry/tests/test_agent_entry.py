# Modified 2026-10-17: test package guidance and independent Desktop/IDE/CLI detection.
# Modified 2026-10-20: cover raising a running GUI window; isolate desktop lookup from the host.
# Apache-2.0; see ../LICENSE, ../NOTICE and ../ORIGIN.md.
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("agent_entry", ROOT / "agent_entry.py")
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class EntryTest(unittest.TestCase):
    def setUp(self) -> None:
        locale = patch.dict(entry.os.environ, {"LC_ALL": "zh_CN.UTF-8"})
        locale.start()
        self.addCleanup(locale.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        environment = patch.dict(entry.os.environ, {"XDG_CONFIG_HOME": self.temp.name})
        environment.start()
        self.addCleanup(environment.stop)
        self.cfg = Path(self.temp.name) / "agent-entry.json"
        self.patcher = patch.object(entry, "config_path", return_value=self.cfg)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_aw_entry_uses_packaged_launcher_without_replacing_qoder(self) -> None:
        lookup = lambda name: name if name == "/usr/bin/aw-launch" else ("/usr/bin/qodercli" if name == "qodercli" else None)
        with patch.object(entry, "which", side_effect=lookup):
            self.assertEqual(entry.command_for(entry.get_agent("aw")), ["/usr/bin/aw-launch"])
            self.assertEqual(entry.command_for(entry.get_agent("qoder-cli")), ["/usr/bin/qodercli"])
        with patch.object(entry, "command_for", return_value=["/usr/bin/aw-launch"]), patch.object(entry.subprocess, "run") as run:
            entry.session("aw", self.temp.name)
            self.assertEqual(run.call_args.args[0], ["/usr/bin/aw-launch"])
            self.assertTrue(run.call_args.kwargs["check"])

    def test_custom_aw_launcher_does_not_probe_packaged_state(self):
        entry.save_config({"version": 1, "commands": {"aw": ["/custom/aw"]}, "agents": []})
        with patch.object(entry._aw, "snapshot") as snapshot:
            self.assertEqual(entry.snapshot()["aw"]["state"], "unsupported_launcher")
            snapshot.assert_not_called()

    def test_status_without_aw_configuration_does_not_spawn_or_read_credentials(self) -> None:
        with patch.object(entry, "which", return_value=None), patch.object(
            entry.subprocess, "Popen"
        ) as spawn:
            result = entry.snapshot()
            self.assertGreaterEqual(len(result["agents"]), 5)
            self.assertFalse(any(a["available"] for a in result["agents"]))
            spawn.assert_not_called()

    def test_return_focuses_existing_session_instead_of_duplicate_attachment(self):
        key = 'a' * 32
        with patch.object(entry._workspace, 'snapshot', return_value={'sessions': [{'id': key, 'pid': 123}]}), patch.object(entry, 'focus_running', return_value=True) as focus, patch.object(entry, 'open_terminal') as terminal:
            entry.return_session(key, self.temp.name)
            self.assertTrue(entry.re.fullmatch(focus.call_args.args[0], 'anolisa-session-' + key))
            terminal.assert_not_called()

    def test_expired_return_never_opens_an_agent_or_window(self):
        with patch.object(entry._workspace, 'snapshot', return_value={'sessions': []}), patch.object(entry, 'open_terminal') as terminal:
            with self.assertRaises(ValueError):
                entry.return_session('a' * 32, self.temp.name)
            terminal.assert_not_called()

    def test_existing_cosh_window_returns_to_ai_shell_without_launching_qoder(self):
        with patch.object(entry, 'command_for', return_value=['/usr/bin/cosh']), patch.object(entry, 'focus_running', return_value=True), patch.object(entry._workspace, 'focus_shell') as home, patch.object(entry, 'open_terminal') as terminal:
            entry.launch('cosh', self.temp.name)
            home.assert_called_once_with(Path(self.temp.name).resolve())
            terminal.assert_not_called()

    def test_argument_injection_is_not_shell(self) -> None:
        args = type(
            "Args",
            (),
            dict(
                id="example",
                name="Example",
                kind="terminal",
                value='["echo", "$(touch /tmp/never)"]',
            ),
        )()
        entry.register(args)
        self.assertEqual(entry.get_agent("local.example")["argv"][1], "$(touch /tmp/never)")
        with patch.object(entry.subprocess, "Popen") as spawn:
            entry.detach(["echo", "$(touch /tmp/never)"])
            self.assertNotIn("shell", spawn.call_args.kwargs)
            self.assertTrue(spawn.call_args.kwargs["start_new_session"])

    def test_register_web_and_duplicate(self) -> None:
        args = type(
            "Args",
            (),
            dict(id="console", name="Console", kind="web", value="http://127.0.0.1:19820"),
        )()
        entry.register(args)
        self.assertEqual(entry.get_agent("local.console")["kind"], "web")
        with self.assertRaises(ValueError):
            entry.register(args)

    def test_invalid_web_and_commands(self) -> None:
        for url in ("file:///etc/passwd", "javascript:alert(1)", "https://user:pass@example.com"):
            with self.assertRaises(ValueError):
                entry.valid_url(url)
        for argv in ([], "echo hi", ["echo", "bad\narg"], [1]):
            with self.assertRaises(ValueError):
                entry.valid_argv(argv)

    def test_bad_config_is_not_overwritten(self) -> None:
        self.cfg.write_text("not JSON")
        with self.assertRaises(ValueError):
            entry.load_config()
        self.assertEqual(self.cfg.read_text(), "not JSON")

    def test_project_requires_directory(self) -> None:
        with self.assertRaises(ValueError):
            entry.project_dir(str(Path(self.temp.name) / "absent"))
        self.assertEqual(entry.project_dir(self.temp.name), Path(self.temp.name).resolve())

    def test_gui_does_not_resolve_cli_name(self) -> None:
        item = entry.get_agent("qoder")
        with patch.object(
            entry, "which", side_effect=lambda s: "/bin/qoder" if s == "qoder" else None
        ):
            self.assertIsNone(entry.command_for(item))

    def test_unknown_id(self) -> None:
        with self.assertRaises(ValueError):
            entry.launch("not-an-agent", self.temp.name)

    def test_terminal_payload_is_argument_array(self) -> None:
        with patch.object(
            entry, "which", side_effect=lambda s: "/usr/bin/foot" if s == "foot" else None
        ):
            argv = entry.terminal_argv(["echo", "a b; c"], Path("/tmp/a b"))
            self.assertEqual(argv[-1], "a b; c")
            self.assertIn("--working-directory=/tmp/a b", argv)

    def test_cli_does_not_resolve_desktop_command(self) -> None:
        with patch.object(entry, "which", side_effect=lambda s: "/usr/bin/qoder" if s == "qoder" else None):
            self.assertIsNone(entry.command_for(entry.get_agent("qoder-cli")))

    def test_cli_resolves_only_qodercli(self) -> None:
        with patch.object(entry, "which", side_effect=lambda s: "/usr/bin/qodercli" if s == "qodercli" else None):
            self.assertEqual(entry.command_for(entry.get_agent("qoder-cli")), ["/usr/bin/qodercli"])

    def test_desktop_and_ide_are_independent(self) -> None:
        home = Path(self.temp.name)
        applications = home / ".local/share/applications"
        applications.mkdir(parents=True)
        (applications / "qoder-ide.desktop").write_text("[Desktop Entry]\n")
        lookup = lambda s: "/usr/bin/gtk-launch" if s == "gtk-launch" else None
        # desktop_dirs keeps the real /usr/share/applications out of the result: a
        # host with Qoder installed otherwise answers for the empty temp directory.
        with patch.object(entry.Path, "home", return_value=home), patch.object(
            entry, "desktop_dirs", return_value=[applications]
        ), patch.object(entry, "which", side_effect=lookup):
            self.assertIsNone(entry.command_for(entry.get_agent("qoder")))
            self.assertEqual(entry.command_for(entry.get_agent("qoder-ide")), ["/usr/bin/gtk-launch", "qoder-ide"])
            (applications / "qoder-ide.desktop").unlink()
            (applications / "qoder.desktop").write_text("[Desktop Entry]\n")
            self.assertEqual(entry.command_for(entry.get_agent("qoder")), ["/usr/bin/gtk-launch", "qoder"])
            self.assertIsNone(entry.command_for(entry.get_agent("qoder-ide")))

    def gui_environment(self, desktop_text: str):
        home = Path(self.temp.name)
        applications = home / ".local/share/applications"
        applications.mkdir(parents=True, exist_ok=True)
        (applications / "qoder.desktop").write_text(desktop_text, encoding="utf-8")
        lookup = lambda s: {
            "gtk-launch": "/usr/bin/gtk-launch",
            "omarchy": "/usr/bin/omarchy",
        }.get(s)
        return home, applications, lookup

    def test_class_pattern_is_anchored_and_read_from_the_desktop_file(self) -> None:
        home, applications, lookup = self.gui_environment("[Desktop Entry]\nStartupWMClass=qoder\n")
        argv = ["/usr/bin/gtk-launch", "qoder"]
        with patch.object(entry.Path, "home", return_value=home), patch.object(
            entry, "desktop_dirs", return_value=[applications]
        ), patch.object(entry, "which", side_effect=lookup):
            # Anchored so "qoder" cannot match a "qoder-ide" window.
            self.assertEqual(entry.desktop_window_class(argv), "^qoder$")
        home, applications, lookup = self.gui_environment("[Desktop Entry]\n")
        with patch.object(entry.Path, "home", return_value=home), patch.object(
            entry, "desktop_dirs", return_value=[applications]
        ):
            self.assertEqual(entry.desktop_window_class(argv), "^qoder$")
        self.assertIsNone(entry.desktop_window_class(["/usr/bin/cosh-ng"]))
        self.assertIsNone(
            entry.desktop_window_class(["/usr/bin/gtk-launch", "absent-entry"])
        )

    def test_running_gui_window_is_raised_instead_of_respawned(self) -> None:
        home, applications, lookup = self.gui_environment("[Desktop Entry]\nStartupWMClass=qoder\n")
        ok = type("Result", (), {"returncode": 0})()
        with patch.object(entry.Path, "home", return_value=home), patch.object(
            entry, "desktop_dirs", return_value=[applications]
        ), patch.object(entry, "which", side_effect=lookup), patch.object(
            entry.subprocess, "run", return_value=ok
        ) as focus, patch.object(entry.subprocess, "Popen") as spawn:
            message = entry.launch("qoder")
        self.assertEqual(
            focus.call_args.args[0], ["/usr/bin/omarchy", "hyprland", "focus", "app", "^qoder$"]
        )
        spawn.assert_not_called()
        self.assertIn("已在运行", message)

    def test_gui_still_launches_when_no_window_is_found(self) -> None:
        home, applications, lookup = self.gui_environment("[Desktop Entry]\nStartupWMClass=qoder\n")
        absent = type("Result", (), {"returncode": 1})()
        with patch.object(entry.Path, "home", return_value=home), patch.object(
            entry, "desktop_dirs", return_value=[applications]
        ), patch.object(entry, "which", side_effect=lookup), patch.object(
            entry.subprocess, "run", return_value=absent
        ), patch.object(entry.subprocess, "Popen") as spawn:
            message = entry.launch("qoder")
        self.assertEqual(spawn.call_args.args[0], ["/usr/bin/gtk-launch", "qoder"])
        self.assertTrue(spawn.call_args.kwargs["stdout"], "the app must not hold the helper's pipes")
        self.assertIn("已发起启动请求", message)

    def test_focus_is_skipped_without_the_compositor_helper(self) -> None:
        home, applications, _ = self.gui_environment("[Desktop Entry]\nStartupWMClass=qoder\n")
        lookup = lambda s: "/usr/bin/gtk-launch" if s == "gtk-launch" else None
        with patch.object(entry.Path, "home", return_value=home), patch.object(
            entry, "desktop_dirs", return_value=[applications]
        ), patch.object(entry, "which", side_effect=lookup), patch.object(
            entry.subprocess, "run"
        ) as focus, patch.object(entry.subprocess, "Popen") as spawn:
            message = entry.launch("qoder")
        focus.assert_not_called()
        spawn.assert_called()
        self.assertIn("已发起启动请求", message)

    def test_package_guidance_is_specific_and_only_opens_browser(self) -> None:
        expected = {
            "aw": "aw-preview",
            "qoder": "qoder-bin",
            "qoder-ide": "qoder-ide-bin",
            "qoder-cli": "qodercli-bin",
            "qoderwake": "qoderwake-bin",
        }
        for agent_id, package in expected.items():
            with self.subTest(agent_id=agent_id):
                docs = entry.get_agent(agent_id)["docs"]
                self.assertEqual(docs, "https://github.com/casparant/useful-omarchy-softwares/blob/main/pkgbuilds/" + package + "/README.md")
                with patch.object(entry.sys, "argv", ["agent_entry.py", "docs", agent_id]), patch.object(entry, "open_url") as browser, patch.object(entry.subprocess, "run") as run:
                    self.assertEqual(entry.main(), 0)
                    browser.assert_called_once_with(docs)
                    run.assert_not_called()

    def test_installable_flag_needs_missing_launcher_and_tools(self) -> None:
        with patch.object(entry, "tools_launcher", return_value="/repo/omarchy-tools"), patch.object(
            entry, "which", return_value=None
        ):
            states = {a["id"]: (a["available"], a["installable"]) for a in entry.snapshot()["agents"]}
        self.assertEqual(states["qoderwake"], (False, True))
        self.assertEqual(states["aw"], (False, True))
        # cosh and codex are not in this repository's software catalog.
        self.assertEqual(states["cosh"], (False, False))
        self.assertEqual(states["codex"], (False, False))
        with patch.object(entry, "tools_launcher", return_value=None), patch.object(
            entry, "which", return_value=None
        ):
            self.assertFalse(any(a["installable"] for a in entry.snapshot()["agents"]))

    def test_install_action_opens_terminal_with_argument_array(self) -> None:
        lookup = lambda name: "/usr/bin/foot" if name == "foot" else None
        with patch.object(entry, "tools_launcher", return_value="/repo/omarchy-tools"), patch.object(
            entry, "which", side_effect=lookup
        ), patch.object(entry.subprocess, "Popen") as spawn, patch.object(entry.subprocess, "run") as run:
            message = entry.install("qoder-ide", self.temp.name)
        payload = spawn.call_args.args[0]
        self.assertEqual(payload[0], "/usr/bin/foot")
        self.assertIn("-e", payload)
        self.assertIn("install-run", payload)
        self.assertIn("qoder-ide", payload)
        self.assertNotIn("shell", spawn.call_args.kwargs)
        run.assert_not_called()
        self.assertIn("已在新终端中开始安装", message)

    def test_install_run_delegates_to_repository_tools(self) -> None:
        with patch.object(entry, "tools_launcher", return_value="/repo/omarchy-tools"), patch.object(
            entry.subprocess, "run"
        ) as run:
            entry.install_run("qoder-cli", self.temp.name)
        self.assertEqual(run.call_args.args[0], ["/repo/omarchy-tools", "install", "qodercli"])
        self.assertTrue(run.call_args.kwargs["check"])
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_install_rejects_unmapped_entry_and_missing_tools(self) -> None:
        with patch.object(entry, "tools_launcher", return_value="/repo/omarchy-tools"):
            with self.assertRaises(ValueError):
                entry.install("codex", self.temp.name)
        with patch.object(entry, "tools_launcher", return_value=None):
            with self.assertRaises(ValueError):
                entry.install("qoderwake", self.temp.name)

    def test_install_subcommands_are_registered(self) -> None:
        for action in ("install", "install-run"):
            with patch.object(entry.sys, "argv", ["agent_entry.py", action, "--help"]):
                with self.assertRaises(SystemExit) as error:
                    entry.main()
            self.assertEqual(error.exception.code, 0, action)

    def test_legacy_codex_installation_is_still_discovered(self) -> None:
        home = Path(self.temp.name)
        legacy = home / ".local/share/anolisa/agent-entry/npm/bin/codex"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("#!/bin/sh\nexit 0\n")
        legacy.chmod(0o755)
        with patch.object(entry.Path, "home", return_value=home), patch.dict(entry.os.environ, {"PATH": "/nonexistent"}):
            self.assertEqual(entry.command_for(entry.get_agent("codex")), [str(legacy)])

    def test_current_codex_installation_precedes_legacy_fallback(self) -> None:
        home = Path(self.temp.name)
        legacy = home / ".local/share/anolisa/agent-entry/npm/bin/codex"
        current = home / "current-bin/codex"
        for executable in (legacy, current):
            executable.parent.mkdir(parents=True)
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
        with patch.object(entry.Path, "home", return_value=home), patch.dict(entry.os.environ, {"PATH": str(current.parent)}):
            self.assertEqual(entry.command_for(entry.get_agent("codex")), [str(current)])

    def test_wake_requires_explicit_launch_and_local_listener(self) -> None:
        result = type("Result", (), {"returncode": 0})()
        with patch.object(entry, "command_for", return_value=["/usr/bin/qoderwake"]), patch.object(entry.subprocess, "run", return_value=result) as run:
            entry.session("qoderwake", self.temp.name)
            self.assertEqual(run.call_args_list[0].args[0], ["/usr/bin/qoderwake", "whoami"])
            self.assertEqual(run.call_args_list[1].args[0], ["/usr/bin/qoderwake", "start", "--host", "127.0.0.1", "--open"])
            self.assertEqual(len(run.call_args_list), 2)

    def test_manifest(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text())
        self.assertEqual(manifest["id"], entry.PLUGIN_ID)
        self.assertIn("panel", manifest["kinds"])
        for file in manifest["entryPoints"].values():
            self.assertTrue((ROOT / file).is_file())
            self.assertNotIn("..", file)


if __name__ == "__main__":
    unittest.main()
