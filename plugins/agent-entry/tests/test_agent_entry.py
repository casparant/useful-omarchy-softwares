# Modified 2026-10-17: test package guidance and independent Desktop/IDE/CLI detection.
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
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cfg = Path(self.temp.name) / "agent-entry.json"
        self.patcher = patch.object(entry, "config_path", return_value=self.cfg)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_status_does_not_spawn_or_read_credentials(self) -> None:
        with patch.object(entry, "which", return_value=None), patch.object(
            entry.subprocess, "Popen"
        ) as spawn:
            result = entry.snapshot()
            self.assertGreaterEqual(len(result["agents"]), 5)
            self.assertFalse(any(a["available"] for a in result["agents"]))
            spawn.assert_not_called()

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
        with patch.object(entry.Path, "home", return_value=home), patch.object(entry, "which", side_effect=lookup):
            self.assertIsNone(entry.command_for(entry.get_agent("qoder")))
            self.assertEqual(entry.command_for(entry.get_agent("qoder-ide")), ["/usr/bin/gtk-launch", "qoder-ide"])
            (applications / "qoder-ide.desktop").unlink()
            (applications / "qoder.desktop").write_text("[Desktop Entry]\n")
            self.assertEqual(entry.command_for(entry.get_agent("qoder")), ["/usr/bin/gtk-launch", "qoder"])
            self.assertIsNone(entry.command_for(entry.get_agent("qoder-ide")))

    def test_package_guidance_is_specific_and_only_opens_browser(self) -> None:
        expected = {
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

    def test_removed_install_actions_are_rejected(self) -> None:
        for action in ("install", "install-run"):
            with patch.object(entry.sys, "argv", ["agent_entry.py", action, "qoderwake"]):
                with self.assertRaises(SystemExit) as error:
                    entry.main()
                self.assertEqual(error.exception.code, 2)

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
