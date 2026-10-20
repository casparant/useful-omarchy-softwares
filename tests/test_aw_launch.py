"""Protect first-run consent, existing policy, authentication and daily reuse."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SOURCE = Path(__file__).resolve().parents[1] / "pkgbuilds/aw-preview/aw-launch.py"
spec = importlib.util.spec_from_file_location("aw_launch", SOURCE)
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


class LaunchTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.prefix = self.root / "prefix"
        self.qoder = self.root / "qodercli"
        self.qoder.write_text("#!/bin/sh\nexit 0\n")
        self.qoder.chmod(0o755)
        self.calls = []
        self.logged_in = True
        self.backend = True
        self.version = "1.1.71"
        self.document = {"spec": {"agents": {"qoder": {"adapter": "qoder", "argv": [str(self.qoder)]}},
                                  "providers": {}, "events": {"custom": {"steps": ["preserve"]}}}}
        for patch in (
            mock.patch.object(launch, "PREFIX", self.prefix),
            mock.patch.object(launch, "PACKAGED_QODER", self.root / "packaged-qoder"),
            mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.root / "config"),
                                        "XDG_STATE_HOME": str(self.root / "state"),
                                        "QODER_PERSONAL_ACCESS_TOKEN": ""}),
            mock.patch.object(launch.shutil, "which", return_value=str(self.qoder)),
            mock.patch.object(launch, "command", side_effect=self.command),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def command(self, args, **kwargs):
        args = [str(arg) for arg in args]
        self.calls.append(args)
        if args[-1] == "--version":
            return self.version
        if args[-1] == "status":
            return "Account: signed in" if self.logged_in else "Account: Not logged in"
        if args[-1] == "login":
            self.logged_in = True
        if "--health" in args:
            return json.dumps({"backend": "authenticated_reachable" if self.backend else "unavailable"})
        if "configure" in args:
            config = Path(args[args.index("--config") + 1])
            if config.exists():
                raise launch.SetupError("refusing overwrite")
            if args[args.index("--provider") + 1] == "sec-core+tokenless":
                self.document["spec"]["providers"]["security"] = {"transport": {"argv": [
                    str(self.prefix / "libexec/aw/providers/sec-core/aw-provider-sec-core"),
                    "--cli", "unused", "--socket", launch.SOCKET]}}
            config.write_text(json.dumps(self.document))
        if "show" in args:
            return Path(args[-1]).read_text()
        return ""

    def prepare(self, answers=()):
        with mock.patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(io.StringIO()):
            return launch.prepare()

    def existing(self):
        config, _ = launch.paths()
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps(self.document))
        return config

    def test_first_compression_setup_then_reuse_without_changes_or_system_authorization(self):
        args = self.prepare(["", "n"])
        config, _ = launch.paths()
        original = config.read_bytes()
        self.assertEqual(args[-2:], ["--agent", "qoder"])
        self.calls.clear()
        self.assertEqual(self.prepare(), args)
        self.assertEqual(config.read_bytes(), original)
        self.assertFalse(any("configure" in call or call[0] == "/usr/bin/sudo" for call in self.calls))

    def test_packaged_qoder_precedes_stale_user_path(self):
        packaged = self.root / "packaged-qoder"
        packaged.write_bytes(self.qoder.read_bytes())
        packaged.chmod(0o755)
        self.prepare(["", "n"])
        configure = next(call for call in self.calls if "configure" in call)
        self.assertEqual(configure[configure.index("--qoder") + 1], str(packaged))

    def test_desktop_discovers_user_qoder_when_session_path_omits_it(self):
        local = self.root / ".local/bin/qodercli"
        local.parent.mkdir(parents=True)
        local.symlink_to(self.qoder)
        with mock.patch.object(launch.shutil, "which", return_value=None), \
                mock.patch.object(launch.Path, "home", return_value=self.root):
            self.prepare(["", "n"])
        configured = next(call for call in self.calls if "configure" in call)
        self.assertEqual(configured[configured.index("--qoder") + 1], str(local))

    def test_security_requires_explicit_consent_and_authenticated_health(self):
        self.prepare(["", "yes"])
        self.assertIn(["/usr/bin/sudo", "/usr/bin/systemctl", "enable", "--now", launch.UNIT], self.calls)
        self.calls.clear()
        self.prepare()
        self.assertTrue(any("--health" in call for call in self.calls))
        self.assertFalse(any(call[0] == "/usr/bin/sudo" for call in self.calls))

    def test_unavailable_security_never_downgrades_or_writes_initial_policy(self):
        self.backend = False
        with mock.patch.object(launch.time, "monotonic", side_effect=[0, 6]), \
                self.assertRaisesRegex(launch.SetupError, "unavailable"):
            self.prepare(["", "y"])
        self.assertFalse(launch.paths()[0].exists())
        self.assertFalse(any("configure" in call for call in self.calls))

    def test_explicit_activation_waits_for_socket_readiness(self):
        original = self.command
        probes = []
        def command(args, **kwargs):
            if "--health" in args:
                probes.append(args)
                self.backend = len(probes) > 1
            return original(args, **kwargs)
        with mock.patch.object(launch, "command", side_effect=command), \
                mock.patch.object(launch.time, "sleep") as sleep:
            self.prepare(["", "y"])
        self.assertEqual(len(probes), 3)
        sleep.assert_called_once()

    def test_closing_an_error_message_does_not_raise_another_exception(self):
        with mock.patch.object(launch.sys, "argv", ["aw-launch"]), \
                mock.patch.object(launch, "prepare", side_effect=launch.SetupError("unavailable")), \
                mock.patch.object(launch.sys.stdin, "isatty", return_value=True), \
                mock.patch("builtins.input", side_effect=KeyboardInterrupt), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(launch.main(), 1)

    def test_existing_policy_and_custom_steps_remain_byte_for_byte(self):
        config = self.existing()
        original = config.read_bytes()
        self.prepare()
        self.assertEqual(config.read_bytes(), original)
        self.assertEqual(self.document["spec"]["events"]["custom"]["steps"], ["preserve"])

    def test_native_authentication_stays_in_the_aw_managed_session(self):
        config = self.existing()
        original = config.read_bytes()
        self.logged_in = False
        args = self.prepare()
        self.assertEqual(config.read_bytes(), original)
        self.assertEqual(args, [str(self.prefix / "bin/aw"), "run", "--config",
                                str(config), "--agent", "qoder"])
        self.assertFalse(any(call[-1] in ("login", "status") for call in self.calls))

    def test_pat_is_forwarded_in_environment_without_storing_or_printing_it(self):
        config = self.existing()
        self.logged_in = False
        with mock.patch.dict(os.environ, {"QODER_PERSONAL_ACCESS_TOKEN": "temporary-test-secret"}), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.prepare()
        self.assertNotIn("temporary-test-secret", config.read_text() + output.getvalue())
        self.assertFalse(any(call[-1] in ("login", "status") for call in self.calls))

    def test_old_qoder_is_rejected_before_policy_or_service_changes(self):
        for version in ("1.1.59", "1.1.64-rc.1", "not-a-version"):
            self.version = version
            self.calls.clear()
            with self.assertRaisesRegex(launch.SetupError, "1.1.64"):
                self.prepare([""])
            self.assertFalse(launch.paths()[0].exists())
            self.assertFalse(any(call[0] == "/usr/bin/sudo" for call in self.calls))

    def test_invalid_security_choice_has_no_policy_or_service_side_effect(self):
        with self.assertRaisesRegex(launch.SetupError, "yes or no"):
            self.prepare(["", "maybe"])
        self.assertFalse(launch.paths()[0].exists())
        self.assertFalse(any(call[0] == "/usr/bin/sudo" for call in self.calls))

    def test_daily_security_failure_preserves_policy_and_never_starts_backend(self):
        self.prepare(["", "y"])
        config, _ = launch.paths()
        original = config.read_bytes()
        self.calls.clear()
        self.backend = False
        with self.assertRaisesRegex(launch.SetupError, "unavailable"):
            self.prepare()
        self.assertEqual(config.read_bytes(), original)
        self.assertFalse(any(call[0] == "/usr/bin/sudo" for call in self.calls))

    def test_relative_xdg_paths_are_rejected_without_commands(self):
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": "relative"}):
            with self.assertRaisesRegex(launch.SetupError, "absolute"):
                self.prepare()
        self.assertEqual(self.calls, [])

    def test_cancelled_first_setup_never_writes_policy_or_enables_service(self):
        for error in (EOFError, KeyboardInterrupt):
            with mock.patch.object(launch.sys, "argv", ["aw-launch"]), \
                    mock.patch("builtins.input", side_effect=["", error]), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(launch.main(), 130)
            self.assertFalse(launch.paths()[0].exists())
            self.assertFalse(any(call[0] == "/usr/bin/sudo" for call in self.calls))

    def test_root_launch_is_rejected(self):
        with mock.patch.object(launch.os, "getuid", return_value=0):
            with self.assertRaisesRegex(launch.SetupError, "not root"):
                self.prepare()
        self.assertEqual(self.calls, [])

    def test_native_arguments_follow_aw_run_without_permission_bypass(self):
        self.existing()
        with mock.patch.object(launch.sys, "argv", ["aw-launch", "--", "--help"]), \
                mock.patch.object(launch.os, "execv") as execute:
            launch.main()
        args = execute.call_args.args[1]
        self.assertEqual(args[-2:], ["--", "--help"])
        self.assertIn("run", args)
        self.assertNotIn("--dangerously-skip-permissions", args)


if __name__ == "__main__":
    unittest.main()
