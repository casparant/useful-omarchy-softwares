"""Exercise the public entrypoint without installing packages or changing a desktop."""
import contextlib
import copy
import importlib.machinery
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "omarchy-tools"
loader = importlib.machinery.SourceFileLoader("omarchy_tools", str(ENTRYPOINT))
spec = importlib.util.spec_from_loader(loader.name, loader)
cli = importlib.util.module_from_spec(spec)
loader.exec_module(cli)


class PublicEntrypointTests(unittest.TestCase):
    def test_help_and_catalog_work_from_another_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            for arguments in (["--help"], ["panel", "--help"], ["list"]):
                with self.subTest(arguments=arguments):
                    result = subprocess.run([str(ENTRYPOINT)] + arguments, cwd=directory,
                                            capture_output=True, text=True, check=True)
                    self.assertIn("面板", result.stdout)
                    self.assertEqual(result.stderr, "")
            self.assertIn("dingtalk-bin", result.stdout)
            self.assertIn("aarch64", result.stdout)


class DispatchTests(unittest.TestCase):
    def setUp(self):
        patches = (
            mock.patch.object(cli.sys, "platform", "linux"),
            mock.patch.object(cli.os, "geteuid", return_value=1000),
            mock.patch.object(cli.platform, "machine", return_value="x86_64"),
            mock.patch.object(cli.shutil, "which", side_effect=lambda name: "/usr/bin/" + name),
            mock.patch.object(cli.subprocess, "run"),
        )
        self.context = contextlib.ExitStack()
        self.addCleanup(self.context.close)
        self.mocks = [self.context.enter_context(patch) for patch in patches]
        self.process = self.mocks[-1]

    def invoke(self, *arguments):
        self.output, self.errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(self.output), contextlib.redirect_stderr(self.errors):
            return cli.main(list(arguments))

    def commands(self):
        return [call.args[0] for call in self.process.call_args_list]

    def test_aw_one_command_installs_then_deploys_panel_then_launches(self):
        for arch in ("x86_64", "aarch64"):
            with self.subTest(arch=arch), mock.patch.object(cli.platform, "machine", return_value=arch), mock.patch.dict(cli.os.environ, {"WAYLAND_DISPLAY": "wayland-1"}):
                self.process.reset_mock()
                self.assertEqual(self.invoke("aw"), 0)
                self.assertEqual(self.commands()[0], ["sudo", "pacman", "-S", "--needed", "binutils", "fakeroot"])
                builds = [call.kwargs["cwd"].name for call in self.process.call_args_list if call.args[0][0] == "makepkg"]
                self.assertEqual(builds, ["qodercli-bin", "aw-preview"])
                self.assertEqual(self.commands()[-3:], [
                    [sys.executable, str(ROOT / "plugins/agent-entry/install.py"), "--replace"],
                    ["omarchy-shell", "shell", "hide", "anolisa.agent-entry"],
                    ["/usr/bin/aw-launch"],
                ])
                self.assertFalse(any("--noconfirm" in command for command in self.commands()))

    def test_aw_failed_package_never_deploys_or_launches(self):
        self.process.side_effect = [None, subprocess.CalledProcessError(8, ["makepkg"])]
        with mock.patch.dict(cli.os.environ, {"WAYLAND_DISPLAY": "wayland-1"}):
            self.assertEqual(self.invoke("aw"), 8)
        self.assertEqual(len(self.commands()), 2)

    def test_aw_panel_failure_does_not_start_agent(self):
        self.process.side_effect = [None, None, None, None, subprocess.CalledProcessError(1, ["panel"])]
        with mock.patch.dict(cli.os.environ, {"WAYLAND_DISPLAY": "wayland-1"}):
            self.assertEqual(self.invoke("aw"), 1)
        self.assertFalse(any(command[0] == "/usr/bin/aw-launch" for command in self.commands()))

    def test_aw_requires_desktop_before_installation(self):
        with mock.patch.dict(cli.os.environ, {}, clear=True):
            self.assertEqual(self.invoke("aw"), 1)
        self.process.assert_not_called()

    def test_aw_install_alias_uses_binary_recipe(self):
        self.assertEqual(self.invoke("install", "aw", "aw-preview"), 0)
        self.assertEqual(len(self.commands()), 2)
        self.assertEqual(self.process.call_args.kwargs["cwd"].name, "aw-preview")

    def test_local_build_uses_native_user_and_recipe_directory_on_both_architectures(self):
        for arch in ("x86_64", "aarch64"):
            with self.subTest(arch=arch), mock.patch.object(cli.platform, "machine", return_value=arch):
                self.process.reset_mock()
                self.assertEqual(self.invoke("install", "qoderwake"), 0)
                self.assertEqual(self.commands(), [
                    ["sudo", "pacman", "-S", "--needed", "base-devel"],
                    ["makepkg", "--syncdeps", "--install", "--cleanbuild", "--force"],
                ])
                self.assertEqual(self.process.call_args.kwargs["cwd"], ROOT / "pkgbuilds/qoderwake-bin")
                self.assertTrue(all(call.kwargs["check"] for call in self.process.call_args_list))

    def test_clash_uses_its_local_recipe_on_both_architectures(self):
        for arch, name in (("x86_64", "clash-verge-rev"), ("aarch64", "clash-verge-rev-bin")):
            with self.subTest(arch=arch), mock.patch.object(cli.platform, "machine", return_value=arch):
                self.process.reset_mock()
                self.assertEqual(self.invoke("install", name), 0)
                self.assertEqual(self.commands()[-1], ["makepkg", "--syncdeps", "--install", "--cleanbuild", "--force"])
                self.assertEqual(self.process.call_args.kwargs["cwd"], ROOT / "pkgbuilds/clash-verge-rev-bin")
                self.assertFalse(any(command[0] == "omarchy" for command in self.commands()))

    def test_aliases_are_deduplicated_and_update_uses_checkout_recipe(self):
        self.assertEqual(self.invoke("update", "qodercli-bin", "qodercli"), 0)
        self.assertEqual(len(self.commands()), 2)
        self.assertEqual(self.process.call_args.kwargs["cwd"], ROOT / "pkgbuilds/qodercli-bin")

    def test_every_name_is_validated_before_any_installation(self):
        for name in ("missing", "../qoderwake-bin", "--noconfirm", "qoderwake; touch owned"):
            with self.subTest(name=name):
                self.process.reset_mock()
                # '--' makes option-looking input a name, never an extra build flag.
                self.assertEqual(self.invoke("install", "qoderwake", "--", name), 1)
                self.assertIn("未知软件", self.errors.getvalue())
                self.process.assert_not_called()

    def test_entire_batch_architecture_is_checked_before_installation(self):
        with mock.patch.object(cli.platform, "machine", return_value="aarch64"):
            self.assertEqual(self.invoke("install", "qoderwake", "qoder-ide"), 1)
        self.assertIn("不支持当前架构 aarch64", self.errors.getvalue())
        self.process.assert_not_called()

    def test_non_linux_and_root_are_rejected_before_commands(self):
        with mock.patch.object(cli.sys, "platform", "darwin"):
            self.assertEqual(self.invoke("panel"), 1)
            self.assertIn("目标 Arch", self.errors.getvalue())
        with mock.patch.object(cli.os, "geteuid", return_value=0):
            self.assertEqual(self.invoke("install", "qoderwake"), 1)
            self.assertIn("不要 sudo", self.errors.getvalue())
        self.process.assert_not_called()

    def test_missing_makepkg_fails_before_dependency_install(self):
        with mock.patch.object(cli.shutil, "which", side_effect=lambda name: None if name == "makepkg" else "/mock/" + name):
            self.assertEqual(self.invoke("install", "qoderwake"), 1)
        self.assertIn("未找到命令 makepkg", self.errors.getvalue())
        self.process.assert_not_called()

    def test_dingtalk_uses_existing_omarchy_route(self):
        self.assertEqual(self.invoke("install", "dingtalk-bin"), 0)
        self.assertEqual(self.commands(), [
            ["pacman", "-Si", "dingtalk-bin"],
            ["omarchy", "pkg", "add", "dingtalk-bin"],
        ])

    def test_missing_external_package_stops_mixed_batch_before_mutation(self):
        self.process.side_effect = subprocess.CalledProcessError(1, ["pacman", "-Si", "dingtalk-bin"])
        self.assertEqual(self.invoke("install", "qoderwake", "dingtalk"), 1)
        self.assertEqual(self.commands(), [["pacman", "-Si", "dingtalk-bin"]])
        self.assertIn("docs/software/dingtalk.md", self.errors.getvalue())

    def test_failed_build_stops_before_the_next_package(self):
        self.process.side_effect = [None, subprocess.CalledProcessError(8, ["makepkg"])]
        self.assertEqual(self.invoke("install", "qoderwake", "qodercli"), 8)
        self.assertEqual(len(self.commands()), 2)
        self.assertNotIn("安装完成", self.output.getvalue())
        self.assertIn("已停止", self.errors.getvalue())

    def test_failed_dependency_install_never_runs_makepkg(self):
        self.process.side_effect = subprocess.CalledProcessError(1, ["sudo", "pacman"])
        self.assertEqual(self.invoke("install", "qoderwake"), 1)
        self.assertEqual(len(self.commands()), 1)
        self.assertEqual(self.commands()[0][:2], ["sudo", "pacman"])

    def test_panel_delegates_flags_to_self_contained_installer(self):
        for flags in ([], ["--autostart"], ["--replace"], ["--replace", "--autostart"]):
            with self.subTest(flags=flags):
                self.process.reset_mock()
                self.assertEqual(self.invoke("panel", *flags), 0)
                command = self.commands()[-1]
                self.assertEqual(command[:2], [sys.executable, str(ROOT / "plugins/agent-entry/install.py")])
                self.assertEqual(set(command[2:]), set(flags))
                self.assertEqual(self.process.call_args.kwargs["cwd"], ROOT)
                self.assertEqual(self.commands()[0], ["sudo", "pacman", "-S", "--needed", "jq", "xdg-utils"])

    def test_panel_uninstall_does_not_install_dependencies(self):
        self.assertEqual(self.invoke("panel", "--uninstall"), 0)
        self.assertEqual(self.commands(), [[sys.executable, str(ROOT / "plugins/agent-entry/install.py"), "--uninstall"]])

    def test_conflicting_panel_flags_are_rejected(self):
        for flags in (["--replace", "--uninstall"], ["--autostart", "--uninstall"]):
            with self.subTest(flags=flags), self.assertRaises(SystemExit) as error:
                self.invoke("panel", *flags)
            self.assertEqual(error.exception.code, 2)
        self.process.assert_not_called()

    def test_remove_uses_exact_pacman_names_and_preserves_dependencies(self):
        self.assertEqual(self.invoke("remove", "qoderwake", "dingtalk-bin"), 0)
        self.assertEqual(self.commands(), [["sudo", "pacman", "-R", "qoderwake-bin", "dingtalk-bin"]])

    def test_catalog_cannot_supply_an_escaping_recipe_or_option_as_package(self):
        entries = copy.deepcopy(cli.software_entries())
        for field, value in (("recipe", "../qoderwake-bin"), ("install", {"method": "omarchy", "package": "--overwrite"})):
            item = entries[0] if field == "recipe" else next(item for item in entries if item["id"] == "dingtalk")
            original = item[field]
            item[field] = value
            with self.subTest(field=field), mock.patch.object(cli, "software_entries", return_value=entries):
                self.assertEqual(self.invoke("install", item["id"]), 1)
                self.process.assert_not_called()
            item[field] = original

    def test_alias_collision_is_not_silently_resolved(self):
        entries = copy.deepcopy(cli.software_entries())
        entries[-1]["id"] = "qoderwake-bin"
        with mock.patch.object(cli, "software_entries", return_value=entries):
            self.assertEqual(self.invoke("install", "qoderwake-bin"), 1)
        self.assertIn("重复名称", self.errors.getvalue())
        self.process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
