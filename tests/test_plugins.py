"""No-network checks for manifest integrity and public-only standalone plugin exports."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import plugin_lib


class PluginFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / "plugins" / "sample"
        self.directory.mkdir(parents=True)
        self.manifest = {
            "schemaVersion": 1, "id": "sample.launcher", "name": "Sample Launcher",
            "version": "0.1.0", "kinds": ["bar-widget", "panel"],
            "entryPoints": {"barWidget": "Bar.qml", "panel": "Dashboard.qml"},
            "barWidget": {"defaultSection": "right"},
        }
        self.entry = {
            "id": "sample.launcher", "path": "plugins/sample", "status": "candidate",
            "architectures": ["x86_64", "aarch64"],
            "runtime_dependencies": ["omarchy-shell", "quickshell", "python>=3.10"],
            "license": "Apache-2.0", "documentation": "plugins/sample/README.md",
            "files": ["manifest.json", "Bar.qml", "Dashboard.qml", "helper.py", "LICENSE", "README.md"],
        }
        self.save_manifest()
        for name in ["Bar.qml", "Dashboard.qml"]:
            (self.directory / name).write_text("import QtQuick\nItem {}\n")
        (self.directory / "helper.py").write_text("raise RuntimeError('validation must not execute plugin code')\n")
        (self.directory / "LICENSE").write_text("Test license\n")
        (self.directory / "README.md").write_text("Test documentation\n")
        self.save_catalog()

    def save_manifest(self):
        (self.directory / "manifest.json").write_text(json.dumps(self.manifest))

    def save_catalog(self, entries=None):
        (self.root / "plugins/catalog.json").write_text(json.dumps({
            "schema_version": 1, "plugins": [self.entry] if entries is None else entries,
        }))

    def check(self, require_omarchy=False):
        with mock.patch.object(plugin_lib.shutil, "which", return_value=None):
            return plugin_lib.check(self.directory, self.entry, require_omarchy)

    def export(self, destination):
        with mock.patch.object(plugin_lib.shutil, "which", return_value=None):
            return plugin_lib.export(self.directory, self.entry, destination)


class PluginManifestTests(PluginFixture):
    def test_valid_plugin_without_executing_python(self):
        self.assertIn("static checks only", self.check())

    def test_manifest_id_must_match_catalog_and_not_be_reserved(self):
        for value in ["other.launcher", "omarchy.launcher", "sample..launcher", "../launcher"]:
            with self.subTest(value=value):
                self.manifest["id"] = value
                self.save_manifest()
                with self.assertRaisesRegex(ValueError, "manifest id"):
                    self.check()

    def test_schema_version_is_a_json_integer(self):
        for value in ["1", True, 2, None]:
            with self.subTest(value=value):
                self.manifest["schemaVersion"] = value
                self.save_manifest()
                with self.assertRaisesRegex(ValueError, "schemaVersion"):
                    self.check()

    def test_declared_kind_requires_its_entry_point(self):
        del self.manifest["entryPoints"]["panel"]
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "entryPoints.panel"):
            self.check()

    def test_entry_point_path_escape_is_rejected(self):
        for value in ["../outside.qml", "/outside.qml", "./Bar.qml", "Bar.qml\n", "sub\\Bar.qml"]:
            with self.subTest(value=value):
                self.manifest["entryPoints"]["panel"] = value
                self.save_manifest()
                with self.assertRaisesRegex(ValueError, "unsafe plugin path"):
                    self.check()

    def test_entry_point_must_be_exported(self):
        self.entry["files"].remove("Dashboard.qml")
        # Tests are permitted as development sources but cannot become hidden runtime inputs.
        (self.directory / "tests").mkdir()
        (self.directory / "Dashboard.qml").rename(self.directory / "tests" / "Dashboard.qml")
        self.manifest["entryPoints"]["panel"] = "tests/Dashboard.qml"
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "missing from export"):
            self.check()

    def test_symlink_to_inside_or_outside_is_rejected(self):
        original = self.directory / "Bar.qml"
        original.unlink()
        for target in [self.directory / "Dashboard.qml", self.root / "outside.qml"]:
            with self.subTest(target=target):
                original.symlink_to(target)
                with self.assertRaisesRegex(ValueError, "symlinks"):
                    self.check()
                original.unlink()

    def test_symlink_hidden_in_cache_is_also_rejected(self):
        cache = self.directory / "__pycache__"
        cache.mkdir()
        (cache / "link").symlink_to(self.root / "private")
        with self.assertRaisesRegex(ValueError, "symlinks"):
            self.check()

    def test_python_syntax_is_checked_without_running_it(self):
        (self.directory / "helper.py").write_text("if broken\n")
        with self.assertRaises(SyntaxError):
            self.check()

    def test_invalid_bar_placement_is_rejected(self):
        for value in ["invalid", [], None]:
            with self.subTest(value=value):
                self.manifest["barWidget"]["defaultSection"] = value
                self.save_manifest()
                with self.assertRaisesRegex(ValueError, "defaultSection"):
                    self.check()

    def test_omarchy_validation_can_be_required(self):
        with self.assertRaisesRegex(ValueError, "omarchy required"):
            self.check(require_omarchy=True)
        with mock.patch.object(plugin_lib.shutil, "which", return_value="/mock/omarchy"), \
                mock.patch.object(plugin_lib.subprocess, "run") as run:
            detail = plugin_lib.check(self.directory, self.entry, True)
        self.assertIn("omarchy plugin validate passed", detail)
        run.assert_called_once_with(["/mock/omarchy", "plugin", "validate", str(self.directory)], check=True)


class PluginCatalogTests(PluginFixture):
    def test_unknown_plugin_and_traversal_are_not_exportable(self):
        for name in ["private-plugin", "../sample", "/sample", "sample/other"]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    plugin_lib.select_plugin(name, self.root)

    def test_duplicate_id_and_escaping_catalog_path_are_rejected(self):
        duplicate = copy.deepcopy(self.entry)
        duplicate["path"] = "plugins/another"
        self.save_catalog([self.entry, duplicate])
        with self.assertRaisesRegex(ValueError, "duplicate plugin catalog id"):
            plugin_lib.load_catalog(self.root)
        for value in ["../other", "plugins/../other", "plugins/sample/other"]:
            with self.subTest(value=value):
                self.entry["path"] = value
                self.save_catalog()
                with self.assertRaises(ValueError):
                    plugin_lib.load_catalog(self.root)

    def test_export_allowlist_is_required_and_cannot_escape(self):
        for value in [None, [], ["../private"], ["/private"], ["manifest.json", "tests/test_sample.py"]]:
            with self.subTest(value=value):
                self.entry["files"] = value
                self.save_catalog()
                with self.assertRaises(ValueError):
                    plugin_lib.load_catalog(self.root)

    def test_documentation_and_license_must_be_exported(self):
        for name in ["README.md", "LICENSE"]:
            with self.subTest(name=name):
                entry = copy.deepcopy(self.entry)
                entry["files"].remove(name)
                self.save_catalog([entry])
                with self.assertRaisesRegex(ValueError, "must include"):
                    plugin_lib.load_catalog(self.root)

    def test_parent_symlink_cannot_select_external_plugin(self):
        other = self.root / "other-root"
        other.mkdir()
        (other / "plugins").symlink_to(self.root / "plugins", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            plugin_lib.select_plugin("sample", other)


class PluginExportTests(PluginFixture):
    def test_export_has_manifest_at_root_and_only_allowlisted_runtime_sources(self):
        tests = self.directory / "tests"
        tests.mkdir()
        (tests / "test_helper.py").write_text("# Development test\n")
        (self.directory / ".gitignore").write_text("__pycache__/\n")
        cache = self.directory / "__pycache__"
        cache.mkdir()
        (cache / "helper.pyc").write_bytes(b"generated bytecode")
        destination = self.root / "export"
        self.assertEqual(self.export(destination), len(self.entry["files"]))
        self.assertEqual({path.name for path in destination.iterdir()}, set(self.entry["files"]))
        self.assertEqual(json.loads((destination / "manifest.json").read_text())["id"], self.entry["id"])
        self.assertEqual((destination / "helper.py").read_bytes(), (self.directory / "helper.py").read_bytes())

    def test_existing_directory_or_dangling_symlink_is_not_overwritten(self):
        for name, symlink in [("existing", False), ("dangling", True)]:
            with self.subTest(symlink=symlink):
                destination = self.root / name
                if symlink:
                    destination.symlink_to(self.root / "does-not-exist")
                else:
                    destination.mkdir()
                with mock.patch.object(plugin_lib, "check", side_effect=AssertionError("must reject before checking sources")):
                    with self.assertRaisesRegex(ValueError, "already exists"):
                        self.export(destination)
                self.assertTrue(destination.is_symlink() if symlink else destination.is_dir())

    def test_cannot_export_into_own_source_tree(self):
        with self.assertRaisesRegex(ValueError, "inside the plugin"):
            self.export(self.directory / "export")

    def test_unrelated_unlisted_files_block_export(self):
        (self.directory / "downloaded-vendor.tar.gz").write_bytes(b"must not publish")
        destination = self.root / "export"
        with self.assertRaisesRegex(ValueError, "undeclared plugin source"):
            self.export(destination)
        self.assertFalse(destination.exists())

    def test_failed_copy_removes_only_the_new_export(self):
        destination = self.root / "export"
        with mock.patch.object(plugin_lib.shutil, "copy2", side_effect=OSError("simulated disk failure")):
            with self.assertRaisesRegex(OSError, "simulated disk failure"):
                self.export(destination)
        self.assertFalse(destination.exists())
        self.assertTrue((self.directory / "manifest.json").is_file())

    def test_invalid_manifest_does_not_create_export_directory(self):
        self.manifest["entryPoints"]["panel"] = "missing.qml"
        self.save_manifest()
        destination = self.root / "export"
        with self.assertRaisesRegex(ValueError, "missing or escaping"):
            self.export(destination)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
