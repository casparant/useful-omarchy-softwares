# Modified 2026-10-19: bilingual output, locale precedence and language persistence.
# Apache-2.0; see ../LICENSE, ../NOTICE and ../ORIGIN.md.
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bilingual_agent_entry", ROOT / "agent_entry.py")
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)


class LanguageTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.config = self.directory / "agent-entry.json"
        config_patch = patch.object(entry, "config_path", return_value=self.config)
        config_patch.start()
        self.addCleanup(config_patch.stop)
        locale_patch = patch.dict(entry.os.environ, {"LC_ALL": "", "LC_MESSAGES": "", "LANG": ""})
        locale_patch.start()
        self.addCleanup(locale_patch.stop)

    def invoke(self, *args):
        output = io.StringIO()
        with patch.object(entry.sys, "argv", ["agent_entry.py", *args]), contextlib.redirect_stdout(output):
            code = entry.main()
        return code, json.loads(output.getvalue())

    def test_default_and_unrecognized_locales_use_english(self):
        for locale in ("", "C", "POSIX", "en_US.UTF-8", "de_DE.UTF-8", "zhotic"):
            with self.subTest(locale=locale), patch.dict(entry.os.environ, {"LANG": locale}):
                self.assertEqual(entry.language_settings(), {"language": "en", "languagePreference": "auto"})
                self.assertEqual(entry.tr("中文", "English"), "English")

    def test_chinese_locale_variants(self):
        for locale in ("zh", "zh_CN.UTF-8", "zh_TW.UTF-8", "zh-Hans", "ZH-hant@modifier"):
            with self.subTest(locale=locale), patch.dict(entry.os.environ, {"LANG": locale}):
                self.assertEqual(entry.language_settings()["language"], "zh")
                self.assertEqual(entry.tr("中文", "English"), "中文")

    def test_locale_precedence(self):
        cases = [
            ({"LC_ALL": "en_US.UTF-8", "LC_MESSAGES": "zh_CN.UTF-8", "LANG": "zh_TW.UTF-8"}, "en"),
            ({"LC_ALL": "zh_CN.UTF-8", "LC_MESSAGES": "en_US.UTF-8", "LANG": "en_US.UTF-8"}, "zh"),
            ({"LC_ALL": "", "LC_MESSAGES": "en_US.UTF-8", "LANG": "zh_CN.UTF-8"}, "en"),
            ({"LC_ALL": "", "LC_MESSAGES": "zh_TW.UTF-8", "LANG": "en_US.UTF-8"}, "zh"),
            ({"LC_ALL": "C", "LC_MESSAGES": "zh_CN.UTF-8", "LANG": "zh_CN.UTF-8"}, "en"),
        ]
        for environ, expected in cases:
            with self.subTest(environ=environ), patch.dict(entry.os.environ, environ):
                self.assertEqual(entry.language_settings()["language"], expected)

    def test_language_command_persists_and_reports_selection(self):
        with patch.dict(entry.os.environ, {"LANG": "zh_CN.UTF-8"}):
            code, result = self.invoke("language", "en")
            self.assertEqual(code, 0)
            self.assertEqual(result, {"message": "Language preference saved", "language": "en", "languagePreference": "en"})
            self.assertEqual(entry.load_config()["language"], "en")
            self.assertEqual(next(item for item in entry.catalog() if item["id"] == "cosh")["subtitle"], "Interactive terminal")
            code, result = self.invoke("language", "zh")
            self.assertEqual(code, 0)
            self.assertEqual(result["language"], "zh")
            self.assertEqual(result["message"], "语言偏好已保存")
            code, result = self.invoke("language", "auto")
            self.assertEqual(code, 0)
            self.assertEqual(result["language"], "zh")
            self.assertEqual(result["languagePreference"], "auto")
            self.assertEqual(entry.load_config()["language"], "auto")

    def test_language_command_requires_a_value(self):
        with patch.object(entry.sys, "argv", ["agent_entry.py", "language"]), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                entry.main()
        self.assertEqual(error.exception.code, 2)
        self.assertFalse(self.config.exists())

    def test_language_update_preserves_custom_data(self):
        original = {
            "version": 1,
            "project": str(self.directory),
            "commands": {"cosh": ["/custom/tool", "你好"]},
            "agents": [{"id": "local.mine", "name": "我的 Tool", "subtitle": "自定义说明", "kind": "web", "url": "https://example.com"}],
            "customFutureField": {"note": "untouched"},
        }
        entry.save_config(original)
        self.assertEqual(self.invoke("language", "en")[0], 0)
        self.assertEqual(entry.load_config(), dict(original, language="en"))
        with patch.object(entry, "which", return_value=None):
            item = next(a for a in entry.snapshot()["agents"] if a["id"] == "local.mine")
        self.assertEqual(item["name"], "我的 Tool")
        self.assertEqual(item["subtitle"], "自定义说明")
        self.assertEqual(item["status"], "Web entry configured")

    def test_snapshot_strings_follow_language_without_spawning(self):
        with patch.object(entry, "which", return_value=None), patch.object(entry.subprocess, "Popen") as spawn:
            for language, missing, subtitle in (("en", "Launcher not found", "Command-line agent"), ("zh", "尚未发现启动入口", "终端版 · 非桌面客户端")):
                self.assertEqual(self.invoke("language", language)[0], 0)
                code, result = self.invoke("status")
                self.assertEqual(code, 0)
                self.assertEqual(result["language"], language)
                self.assertEqual(result["languagePreference"], language)
                codex = next(item for item in result["agents"] if item["id"] == "codex")
                self.assertEqual(codex["status"], missing)
                self.assertEqual(codex["subtitle"], subtitle)
            spawn.assert_not_called()

    def test_regular_action_reports_current_language(self):
        self.invoke("language", "en")
        code, result = self.invoke("project", str(self.directory))
        self.assertEqual(code, 0)
        self.assertEqual(result["message"], "Project folder saved")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["languagePreference"], "en")
        self.assertEqual(entry.load_config()["language"], "en")

    def test_errors_are_localized_and_include_language(self):
        for language, expected in (("en", "Project folder does not exist: "), ("zh", "项目目录不存在：")):
            self.invoke("language", language)
            code, result = self.invoke("project", str(self.directory / "missing"))
            self.assertEqual(code, 1)
            self.assertTrue(result["error"].startswith(expected))
            self.assertEqual(result["language"], language)

    def test_corrupt_config_never_recurses_or_overwrites(self):
        for locale, prefix in (("en_US.UTF-8", "Invalid JSON configuration: "), ("zh_CN.UTF-8", "配置不是有效 JSON：")):
            with self.subTest(locale=locale), patch.dict(entry.os.environ, {"LANG": locale}):
                self.config.write_text("not json", encoding="utf-8")
                code, result = self.invoke("language", "en")
                self.assertEqual(code, 1)
                self.assertTrue(result["error"].startswith(prefix))
                self.assertEqual(self.config.read_text(), "not json")

    def test_invalid_language_config_is_not_silently_replaced(self):
        entry.save_config({"version": 1, "project": str(self.directory), "agents": [], "language": "fr"})
        original = self.config.read_text()
        code, result = self.invoke("status")
        self.assertEqual(code, 1)
        self.assertEqual(result["error"], "language must be auto, en or zh")
        self.assertEqual(result["language"], "en")
        self.assertEqual(result["languagePreference"], "auto")
        self.assertEqual(self.config.read_text(), original)

    def test_terminal_messages_are_localized(self):
        entry.save_config({"version": 1, "project": str(self.directory), "agents": [], "language": "en"})
        output = io.StringIO()
        with patch.object(entry, "command_for", return_value=["/usr/bin/codex"]), patch.object(entry.subprocess, "run") as run, contextlib.redirect_stdout(output):
            entry.session("codex", str(self.directory))
        self.assertIn("Project folder: " + str(self.directory.resolve()), output.getvalue())
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["/usr/bin/codex"])


if __name__ == "__main__":
    unittest.main()
