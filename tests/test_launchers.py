"""Wrapper unit tests only: no native vendor executable, login, or daemon runs.

Each test executes the real packaged shell wrapper with only its absolute vendor
executable path replaced by a temporary inert stub. The stub records arguments,
working directory, and selected environment values. This does not establish that
QoderWake or Qoder CLI runs on Linux or that their settings work at runtime.
"""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_CLI = "/opt/qoderwake/qodercli/qodercli-wake"
CLI_SETTINGS = "/usr/share/qodercli/pacman-settings.json"


class LauncherFixture(unittest.TestCase):
    recipe = None
    vendor = None
    shell = None

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="qoder-wrapper-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.home = self.root / "home"
        self.cwd = self.root / "working directory with spaces"
        self.home.mkdir()
        self.cwd.mkdir()
        self.marker = self.root / "vendor-stub-called"
        self.recorder = self.root / "record.py"
        self.recorder.write_text(
            "import json, os, pathlib, sys\n"
            "pathlib.Path(os.environ['WRAPPER_TEST_MARKER']).write_text('called')\n"
            "print(json.dumps({\n"
            "    'args': sys.argv[1:], 'cwd': os.getcwd(),\n"
            "    'env': {key: os.environ.get(key) for key in\n"
            "            ['HOME', 'QODER_ENV', 'QODERCLI_PATH', 'WRAPPER_TEST_SENTINEL']}\n"
            "}))\n"
            "sys.exit(int(os.environ.get('WRAPPER_TEST_EXIT_CODE', '0')))\n"
        )
        stub = self.root / "vendor-stub"
        stub.write_text(
            '#!/bin/sh\nexec "$WRAPPER_TEST_PYTHON" -B "$WRAPPER_TEST_RECORDER" "$@"\n'
        )
        stub.chmod(0o755)
        source = (ROOT / self.recipe).read_text()
        self.assertEqual(source.count(self.vendor), 1, "vendor exec path must be replaced exactly once")
        self.wrapper = self.root / "wrapper"
        self.wrapper.write_text(source.replace(self.vendor, shlex.quote(str(stub))))
        self.shell_path = shutil.which(self.shell)
        if self.shell_path is None:
            self.skipTest(self.shell + " is needed to execute the real wrapper")
        # Deliberately avoid inheriting credentials or host shell/Python startup settings.
        self.environment = {
            "PATH": os.defpath,
            "HOME": str(self.home),
            "PYTHONDONTWRITEBYTECODE": "1",
            "WRAPPER_TEST_PYTHON": sys.executable,
            "WRAPPER_TEST_RECORDER": str(self.recorder),
            "WRAPPER_TEST_MARKER": str(self.marker),
            "WRAPPER_TEST_SENTINEL": "environment value with spaces; literal",
        }

    def run_wrapper(self, args, extra_environment=None):
        environment = dict(self.environment)
        environment.update(extra_environment or {})
        result = subprocess.run(
            [self.shell_path, str(self.wrapper)] + args,
            cwd=self.cwd, env=environment, text=True, capture_output=True,
            timeout=10,
        )
        self.assertEqual(list(self.home.iterdir()), [], "wrapper/stub must not write to HOME")
        return result

    def record(self, args, extra_environment=None):
        result = self.run_wrapper(args, extra_environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.marker.is_file())
        return json.loads(result.stdout)

    def assert_common_state(self, record):
        self.assertEqual(record["cwd"], str(self.cwd))
        self.assertEqual(record["env"]["HOME"], str(self.home))
        self.assertEqual(
            record["env"]["WRAPPER_TEST_SENTINEL"],
            self.environment["WRAPPER_TEST_SENTINEL"],
        )


class WakeLauncherTests(LauncherFixture):
    recipe = "pkgbuilds/qoderwake-bin/qoderwake-launcher"
    vendor = "/opt/qoderwake/qoderwake"
    shell = "bash"

    def test_arguments_cwd_environment_and_private_cli(self):
        args = ["portal", "argument with spaces", "literal;argument", "--url", "$HOME"]
        record = self.record(args, {"QODER_ENV": "test", "QODERCLI_PATH": "/wrong/standalone-cli"})
        self.assertEqual(record["args"], args)
        self.assertEqual(record["env"]["QODERCLI_PATH"], PRIVATE_CLI)
        self.assertEqual(record["env"]["QODER_ENV"], "test")
        self.assert_common_state(record)

    def test_default_environment_is_production(self):
        record = self.record(["--version"])
        self.assertEqual(record["env"]["QODER_ENV"], "prod")
        self.assertEqual(record["env"]["QODERCLI_PATH"], PRIVATE_CLI)

    def test_empty_environment_uses_production_default(self):
        record = self.record(["--help"], {"QODER_ENV": ""})
        self.assertEqual(record["env"]["QODER_ENV"], "prod")

    def test_no_arguments_are_forwarded_as_no_arguments(self):
        self.assertEqual(self.record([])["args"], [])

    def test_direct_update_commands_never_launch_vendor(self):
        for command in ["update", "upgrade", "self-update"]:
            with self.subTest(command=command):
                result = self.run_wrapper([command, "argument with spaces"])
                self.assertEqual(result.returncode, 1)
                self.assertIn("pacman", result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertFalse(self.marker.exists())

    def test_vendor_exit_status_is_preserved(self):
        result = self.run_wrapper(["status"], {"WRAPPER_TEST_EXIT_CODE": "23"})
        self.assertEqual(result.returncode, 23)
        self.assertTrue(self.marker.exists())


class CLILauncherTests(LauncherFixture):
    recipe = "pkgbuilds/qodercli-bin/qodercli.sh"
    vendor = "/opt/qodercli/qodercli"
    shell = "sh"

    def test_settings_are_prepended_without_changing_user_arguments(self):
        args = ["chat", "argument with spaces", "literal;argument", "$HOME"]
        record = self.record(args, {"QODER_ENV": "test", "QODERCLI_PATH": "/user/selected-cli"})
        self.assertEqual(record["args"], ["--settings", CLI_SETTINGS] + args)
        self.assertEqual(record["env"]["QODER_ENV"], "test")
        self.assertEqual(record["env"]["QODERCLI_PATH"], "/user/selected-cli")
        self.assert_common_state(record)
        settings = json.loads((ROOT / "pkgbuilds/qodercli-bin/pacman-settings.json").read_text())
        self.assertIs(settings["general"]["enableAutoUpdate"], False)

    def test_explicit_user_settings_argument_is_forwarded(self):
        # This checks forwarding order, not native CLI settings precedence.
        args = ["--settings", "user config with spaces.json", "chat", "hello"]
        self.assertEqual(self.record(args)["args"], ["--settings", CLI_SETTINGS] + args)

    def test_direct_update_never_launches_vendor(self):
        result = self.run_wrapper(["update"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("pacman", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.marker.exists())

    def test_vendor_exit_status_is_preserved(self):
        result = self.run_wrapper(["--version"], {"WRAPPER_TEST_EXIT_CODE": "17"})
        self.assertEqual(result.returncode, 17)
        self.assertTrue(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
