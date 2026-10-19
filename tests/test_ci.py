"""Regression checks for native runner planning and disposable install verification."""
import contextlib
import importlib.machinery
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))


def load_tool(name):
    loader = importlib.machinery.SourceFileLoader("ci_test_" + name.replace("-", "_"), str(TOOLS / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


verify = load_tool("ci-verify")
matrix = load_tool("build-matrix")


class VerifyInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "output"
        self.output.mkdir()
        self.calls = []
        self.version = "1.1.73"
        self.missing = None
        self.old_exists = Path.exists
        self.old_is_file = Path.is_file

    def invoke(self, package):
        recipe = self.root / "pkgbuilds" / package
        recipe.mkdir(parents=True)
        (recipe / ".SRCINFO").write_text(
            "pkgbase = {0}\npkgname = {0}\npkgver = 1.1.73\npkgrel = 1\n"
            "arch = x86_64\nlicense = MIT\n".format(package)
        )
        (self.output / (package + "-1.1.73-1-x86_64.pkg.tar.zst")).touch()

        def exists(path):
            return True if str(path) == "/.dockerenv" else self.old_exists(path)

        def is_file(path):
            if str(path).startswith(("/opt/", "/usr/share/qoder-ide/", "/usr/bin/clash-verge", "/usr/bin/verge-mihomo")):
                return str(path) != self.missing
            return self.old_is_file(path)

        def run(*args, **kwargs):
            self.calls.append((args, kwargs))
            if args[:2] == ("pacman", "-Qlq"):
                return SimpleNamespace(stdout="/opt/fake/runtime\n/opt/fake/\n", returncode=0)
            return SimpleNamespace(stdout=self.version, returncode=0)

        def subprocess_run(args, **kwargs):
            self.calls.append((tuple(args), kwargs))
            return SimpleNamespace(stdout="libc.so.6 => /usr/lib/libc.so.6", returncode=0 if args[0] == "ldd" else 1)

        with mock.patch.object(verify, "ROOT", self.root), \
                mock.patch.object(sys, "argv", ["ci-verify", package, str(self.output)]), \
                mock.patch.object(verify.os, "geteuid", return_value=0), \
                mock.patch.object(Path, "exists", exists), \
                mock.patch.object(Path, "is_file", is_file), \
                mock.patch.object(verify, "run", side_effect=run), \
                mock.patch.object(verify.subprocess, "run", side_effect=subprocess_run), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            verify.main()
        return output.getvalue()

    def test_ide_main_executable_is_checked_at_real_install_location(self):
        output = self.invoke("qoder-ide-bin")
        commands = [call[0] for call in self.calls]
        self.assertIn(("ldd", "/usr/share/qoder-ide/qoder-ide"), commands)
        self.assertIn(("pacman", "-R", "--noconfirm", "qoder-ide-bin"), commands)
        self.assertNotIn("version/help", output)

    def test_clash_checks_dynamic_helpers_and_static_cores_without_starting_them(self):
        output = self.invoke("clash-verge-rev-bin")
        commands = [call[0] for call in self.calls]
        for name in ("clash-verge", "clash-verge-service", "clash-verge-service-install", "clash-verge-service-uninstall"):
            self.assertIn(("ldd", "/usr/bin/" + name), commands)
        for name in ("verge-mihomo", "verge-mihomo-alpha"):
            self.assertIn(("readelf", "-d", "/usr/bin/" + name), commands)
            self.assertNotIn(("ldd", "/usr/bin/" + name), commands)
        self.assertFalse(any(args[0].startswith("/usr/bin/") for args in commands))
        self.assertNotIn("version/help", output)

    def test_clash_core_dynamic_dependencies_require_review(self):
        self.version = "0x00000001 (NEEDED) Shared library: [libunexpected.so]"
        with self.assertRaisesRegex(ValueError, "gained dynamic dependencies"):
            self.invoke("clash-verge-rev-bin")

    def test_missing_clash_core_cannot_silently_pass(self):
        self.missing = "/usr/bin/verge-mihomo-alpha"
        with self.assertRaisesRegex(ValueError, "missing installed executable"):
            self.invoke("clash-verge-rev-bin")

    def test_missing_ide_executable_cannot_silently_pass(self):
        self.missing = "/usr/share/qoder-ide/qoder-ide"
        with self.assertRaisesRegex(ValueError, "missing installed executable"):
            self.invoke("qoder-ide-bin")

    def test_smoke_home_is_set_after_runuser_resets_its_environment(self):
        self.invoke("qodercli-bin")
        smoke = [(args, kwargs) for args, kwargs in self.calls if args[:5] == ("runuser", "-u", "builder", "--", "env") and args[-1] in ("--version", "--help")]
        self.assertEqual(len(smoke), 2)
        for args, kwargs in smoke:
            self.assertTrue(args[5].startswith("HOME="))
            self.assertIn("qoder-smoke-", args[5])
            self.assertTrue(args[6].startswith("QODER_CONFIG_DIR="))
            self.assertNotIn("env", kwargs)
            self.assertEqual(args[-2], "qodercli")
            self.assertIn(args[-1], ("--version", "--help"))

    def test_metadata_outputs_use_writable_storage_with_source_still_readonly(self):
        self.invoke("qodercli-bin")
        metadata = [args for args, kwargs in self.calls if args[-1:] == ("--require-makepkg",)]
        self.assertEqual(len(metadata), 1)
        arguments = metadata[0]
        self.assertEqual(arguments[:5], ("runuser", "-u", "builder", "--", "env"))
        for name in ("BUILDDIR", "PKGDEST", "SRCDEST", "SRCPKGDEST", "LOGDEST"):
            value = next(arg for arg in arguments if arg.startswith(name + "="))
            self.assertIn("qoder-metadata-", value)

    def test_unexpected_runtime_version_fails(self):
        self.version = "0.0.1"
        with self.assertRaisesRegex(ValueError, "unexpected version"):
            self.invoke("qodercli-bin")

    def test_removal_checks_package_files_as_well_as_pacman_database(self):
        with mock.patch.object(verify.os.path, "lexists", return_value=True):
            with self.assertRaisesRegex(ValueError, "files remained after removal"):
                self.invoke("qoder-ide-bin")


class NativeMatrixTests(unittest.TestCase):
    def test_arm_is_only_scheduled_for_recipes_declaring_arm(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, arches in [("cli-bin", ["x86_64", "aarch64"]), ("gui-bin", ["x86_64"])]:
                directory = root / "pkgbuilds" / name
                directory.mkdir(parents=True)
                (directory / ".SRCINFO").write_text(
                    "pkgbase = {0}\npkgname = {0}\npkgver = 1\npkgrel = 1\nlicense = MIT\n".format(name)
                    + "".join("arch = " + arch + "\n" for arch in arches)
                )
            def recipe(name):
                return root / "pkgbuilds" / name
            with mock.patch.object(matrix, "ROOT", root), \
                    mock.patch.object(matrix, "recipe_dir", side_effect=recipe), \
                    mock.patch.object(sys, "argv", ["build-matrix"]), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                matrix.main()
            import json
            jobs = json.loads(output.getvalue())["include"]
            self.assertEqual(len(jobs), 3)
            arm = [job for job in jobs if job["arch"] == "aarch64"]
            self.assertEqual(arm, [{"package": "cli-bin", "arch": "aarch64", "runner": "ubuntu-24.04-arm"}])


if __name__ == "__main__":
    unittest.main()
