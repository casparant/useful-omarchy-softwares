# Modified 2026-10-19: cover bilingual deploy resources, desktop names and preserved installs.
# Apache-2.0; see ../LICENSE, ../NOTICE and ../ORIGIN.md.
import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("installer", ROOT / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.target = self.home / ".config/omarchy/plugins/anolisa.agent-entry"
        self.hook = self.home / ".config/omarchy/hooks/post-boot.d/anolisa-agent-entry.sh"
        for mock in (
            patch.object(installer.Path, "home", return_value=self.home),
            patch.dict(installer.os.environ, {"XDG_CONFIG_HOME": str(self.home / ".config")}),
            patch.object(installer.sys, "platform", "linux"),
            patch.object(installer.os, "geteuid", return_value=1000),
            patch.object(installer.shutil, "which", return_value="/usr/bin/mock"),
            patch.object(installer, "run"),
            patch.object(installer.subprocess, "run", return_value=SimpleNamespace(returncode=0)),
        ):
            mock.start()
            self.addCleanup(mock.stop)

    def invoke(self, *args: str) -> None:
        with patch.object(installer.sys, "argv", ["install.py", *args]):
            installer.main()

    def test_install_and_recoverable_uninstall(self) -> None:
        other_hook = self.hook.parent / "unrelated.sh"
        other_hook.parent.mkdir(parents=True)
        other_hook.write_text("unchanged")
        config = self.home / ".config/anolisa/agent-entry.json"
        config.parent.mkdir()
        config.write_text('{"version":1,"agents":[]}')
        self.invoke("--autostart")
        self.assertTrue((self.target / "Dashboard.qml").is_file())
        for name in installer.FILES:
            self.assertEqual((self.target / name).read_bytes(), (ROOT / name).read_bytes())
        self.assertFalse((self.target / "qoder").exists())
        self.assertTrue((self.target / "LICENSE").is_file())
        self.assertTrue((self.target / "NOTICE").is_file())
        self.assertTrue((self.target / "install.py").is_file())
        self.assertTrue((self.target / "I18n.js").is_file())
        self.assertTrue((self.target / "i18n.py").is_file())
        self.assertTrue((self.home / ".local/bin/anolisa-agent-entry").is_symlink())
        self.assertIn(" open ", self.hook.read_text())
        self.invoke("--uninstall")
        self.assertFalse(self.target.exists())
        self.assertFalse(self.hook.exists())
        self.assertEqual(other_hook.read_text(), "unchanged")
        self.assertTrue(config.exists())
        self.assertTrue(list((self.home / ".config/anolisa/plugin-backups").glob("removed-*")))

    def test_desktop_menu_has_english_default_and_chinese_locales(self) -> None:
        self.invoke()
        desktop = self.home / ".local/share/applications/anolisa-agent-entry.desktop"
        entries = dict(
            line.split("=", 1) for line in desktop.read_text().splitlines() if "=" in line
        )
        self.assertEqual(entries["Name"], "Agent Entry")
        self.assertEqual(entries["Name[zh_CN]"], "Agent 入口")
        self.assertEqual(entries["Name[zh_TW]"], "Agent 入口")
        self.assertEqual(entries["Comment"], "Launch native agents and terminals")
        self.assertEqual(entries["Comment[zh_CN]"], "启动原生 Agent 与终端")
        self.assertEqual(entries["Comment[zh_TW]"], "啟動原生 Agent 與終端")
        self.assertIn("anolisa-agent-entry", entries["Exec"])
        self.assertTrue(entries["Exec"].endswith(" open"))

    def test_upgrade_backs_up_plugin_and_hook(self) -> None:
        self.invoke("--autostart")
        (self.target / "local-note.txt").write_text("keep this")
        self.invoke("--replace", "--autostart")
        backups = list((self.home / ".config/anolisa/plugin-backups").glob("upgrade-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(
            (backups[0] / "plugins-anolisa.agent-entry/local-note.txt").read_text(), "keep this"
        )
        self.assertTrue(self.hook.exists())


    def test_duplicate_install_requires_replace(self) -> None:
        self.invoke()
        marker = self.target / "local-note.txt"
        marker.write_text("keep this")
        with self.assertRaises(SystemExit) as error:
            self.invoke()
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(marker.read_text(), "keep this")

    def test_legacy_converter_files_stay_in_upgrade_backup(self) -> None:
        self.invoke()
        converter = self.target / "qoder/install.py"
        converter.parent.mkdir()
        converter.write_text("legacy converter")
        self.invoke("--replace")
        self.assertFalse((self.target / "qoder").exists())
        backups = list((self.home / ".config/anolisa/plugin-backups").glob("upgrade-*"))
        self.assertEqual((backups[0] / "plugins-anolisa.agent-entry/qoder/install.py").read_text(), "legacy converter")

    def test_nondefault_config_preserves_official_shell_paths(self) -> None:
        custom = self.home / "custom-config"
        config = custom / "anolisa/agent-entry.json"
        config.parent.mkdir(parents=True)
        config.write_text('{"version":1,"agents":[]}')
        with patch.dict(installer.os.environ, {"XDG_CONFIG_HOME": str(custom)}):
            self.invoke("--autostart")
            self.assertTrue((self.target / "manifest.json").is_file())
            self.assertTrue(self.hook.is_file())
            self.assertFalse((custom / "omarchy").exists())
            (self.target / "local-note.txt").write_text("preserve this")
            self.invoke("--replace", "--autostart")
        backups = list((custom / "anolisa/plugin-backups").glob("upgrade-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "plugins-anolisa.agent-entry/local-note.txt").read_text(), "preserve this")
        self.assertEqual(config.read_text(), '{"version":1,"agents":[]}')

    def test_deployed_source_replace_is_rejected_before_mutation(self) -> None:
        self.invoke()
        marker = self.target / "local-note.txt"
        marker.write_text("keep live plugin")
        deployed_launcher = self.home / ".local/bin/anolisa-agent-entry"
        with patch.object(installer, "SOURCE", self.target), patch.object(installer, "run") as run:
            with self.assertRaises(SystemExit) as error:
                self.invoke("--replace", "--autostart")
            self.assertEqual(error.exception.code, 2)
            run.assert_not_called()
        self.assertEqual(marker.read_text(), "keep live plugin")
        self.assertTrue((self.target / "agent_entry.py").is_file())
        self.assertEqual(deployed_launcher.resolve(), (self.target / "agent_entry.py").resolve())
        self.assertFalse((self.home / ".config/anolisa/plugin-backups").exists())

if __name__ == "__main__":
    unittest.main()
