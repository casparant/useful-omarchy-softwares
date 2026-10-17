"""No-network checks for metadata drift, manifest integrity, and safe AUR export."""
import copy
import contextlib
import io
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import repo_lib


def load_tool(name):
    loader = importlib.machinery.SourceFileLoader(name.replace("-", "_"), str(TOOLS / name))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


checker = load_tool("check-package")
updates = load_tool("check-updates")
exporter = load_tool("export-aur")
HASH_X86 = "a" * 64
HASH_ARM = "b" * 64


class RecipeFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / "pkgbuilds" / "sample-bin"
        self.directory.mkdir(parents=True)
        self.payload = self.directory / "launcher"
        self.payload.write_text("#!/usr/bin/bash\nexec /opt/sample/runtime \"$@\"\n")
        digest = hashlib.sha256(self.payload.read_bytes()).hexdigest()
        (self.directory / "PKGBUILD").write_text("pkgname=sample-bin\npkgver=1.0\npkgrel=1\npackage() { :; }\n")
        self.srcinfo = (
            "pkgbase = sample-bin\n"
            "\tpkgdesc = Test fixture\n"
            "\tpkgver = 1.0\n"
            "\tpkgrel = 1\n"
            "\tarch = x86_64\n"
            "\tarch = aarch64\n"
            "\tlicense = MIT\n"
            "\tsource = launcher\n"
            "\tsha256sums = " + digest + "\n"
            "\tsource_x86_64 = https://example.test/1.0/linux-amd64.tar.gz\n"
            "\tsha256sums_x86_64 = " + HASH_X86 + "\n"
            "\tsource_aarch64 = https://example.test/1.0/linux-arm64.tar.gz\n"
            "\tsha256sums_aarch64 = " + HASH_ARM + "\n"
            "\npkgname = sample-bin\n"
        )
        (self.directory / ".SRCINFO").write_text(self.srcinfo)
        metadata = self.directory / ".omarchy" / "package.json"
        metadata.parent.mkdir()
        metadata.write_text(json.dumps({"source": "local", "sync": False}))
        self.item = {
            "id": "sample",
            "recipe": "pkgbuilds/sample-bin",
            "release_feed": {
                "version_path": "latest", "files_path": "files",
                "architectures": {"x86_64": "amd64", "aarch64": "arm64"},
            },
        }
        self.manifest = {
            "latest": "1.0",
            "files": [
                {"os": "linux", "arch": "amd64", "url": "https://example.test/1.0/linux-amd64.tar.gz", "sha256": HASH_X86},
                {"os": "linux", "arch": "arm64", "url": "https://example.test/1.0/linux-arm64.tar.gz", "sha256": HASH_ARM},
            ],
        }

    def inspect(self, item=None, manifest=None):
        with mock.patch.object(updates, "ROOT", self.root):
            return updates.inspect(item or self.item, manifest or self.manifest)

    def export(self, destination, generated=None):
        with mock.patch.object(exporter.shutil, "which", return_value="/mock/makepkg"), \
                mock.patch.object(exporter, "generated_srcinfo", return_value=generated or self.srcinfo):
            with contextlib.redirect_stdout(io.StringIO()):
                exporter.export(self.directory, destination)


class InputSafetyTests(RecipeFixture):
    def test_local_source_escape_is_rejected(self):
        outside = self.root / "private"
        outside.write_text("not a recipe input")
        self.payload.unlink()
        self.payload.symlink_to(outside)
        fields = repo_lib.read_srcinfo(self.directory / ".SRCINFO")
        with self.assertRaisesRegex(ValueError, "escaping"):
            repo_lib.local_sources(fields, self.directory)
        with mock.patch.object(checker.hashlib, "sha256", side_effect=AssertionError("must validate before hashing")):
            with self.assertRaisesRegex(ValueError, "escaping"):
                checker.check(self.directory)

    def test_traversal_and_download_alias_are_rejected(self):
        for source in ["../private", "/etc/passwd", "../archive::https://example.test/file"]:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    repo_lib.local_sources({"source": [source]}, self.directory)

    def test_srcinfo_symlink_escape_is_rejected(self):
        outside = self.root / "other-srcinfo"
        outside.write_text(self.srcinfo)
        path = self.directory / ".SRCINFO"
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "escaping"):
            repo_lib.read_srcinfo(path)

    def test_parent_symlink_cannot_select_external_recipe(self):
        parent = self.root / "another-repo"
        parent.mkdir()
        (parent / "pkgbuilds").symlink_to(self.root / "pkgbuilds", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "missing package"):
            repo_lib.recipe_dir("sample-bin", parent)

    def test_internal_source_link_is_exportable_as_a_regular_file(self):
        actual = self.directory / "actual-launcher"
        self.payload.rename(actual)
        self.payload.symlink_to(actual.name)
        destination = self.root / "export"
        self.export(destination)
        self.assertFalse((destination / "launcher").is_symlink())
        self.assertEqual((destination / "launcher").read_bytes(), actual.read_bytes())

    def test_literal_ipv6_url_is_not_a_download_alias(self):
        url = "https://[2001:db8::1]/release.tar.gz"
        self.assertEqual(repo_lib.source_target(url), url)


class MetadataTests(RecipeFixture):
    def test_semantic_makepkg_match_ignores_field_order(self):
        fields = repo_lib.read_srcinfo_text(self.srcinfo)
        generated = "pkgbase = sample-bin\n" + "\n".join(
            "{} = {}".format(key, value)
            for key, values in reversed(list(fields.items()))
            if key not in {"pkgbase", "pkgname"} for value in values
        ) + "\npkgname = sample-bin\n"
        with mock.patch.object(checker.shutil, "which", return_value="/mock/makepkg"), \
                mock.patch.object(checker, "generated_srcinfo", return_value=generated):
            fields, detail = checker.check(self.directory, require_makepkg=True)
        self.assertEqual(fields["pkgbase"], ["sample-bin"])
        self.assertIn("matched", detail)

    def test_package_override_scope_is_not_flattened_away(self):
        first = self.srcinfo.replace("\npkgname = sample-bin", "\tdepends = base-lib\n\npkgname = sample-bin") + "\tdepends = package-lib\n"
        second = self.srcinfo.replace("\npkgname = sample-bin", "\tdepends = base-lib\n\tdepends = package-lib\n\npkgname = sample-bin")
        self.assertEqual(repo_lib.read_srcinfo_text(first), repo_lib.read_srcinfo_text(second))
        self.assertFalse(repo_lib.srcinfo_matches(first, second))

    def test_stale_generated_metadata_is_rejected(self):
        generated = self.srcinfo.replace("license = MIT", "license = BSD-3-Clause")
        with mock.patch.object(checker.shutil, "which", return_value="/mock/makepkg"), \
                mock.patch.object(checker, "generated_srcinfo", return_value=generated):
            with self.assertRaisesRegex(ValueError, "SRCINFO differs"):
                checker.check(self.directory, require_makepkg=True)

    def test_local_checksum_drift_is_rejected(self):
        self.payload.write_text("#!/usr/bin/bash\necho changed\n")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            checker.check(self.directory)

    def test_split_package_metadata_is_explicitly_unsupported(self):
        with self.assertRaisesRegex(ValueError, "split packages"):
            repo_lib.read_srcinfo_text(self.srcinfo + "pkgname = second-package\n")

    def test_generated_build_directories_are_not_recipe_inputs(self):
        outside = self.root / "vendor-unrelated.sh"
        outside.write_text("#!/bin/sh\nif broken\n")
        for name in ["src", "pkg", ".git"]:
            generated = self.directory / name
            generated.mkdir()
            (generated / "escaping-vendor.sh").symlink_to(outside)
            (generated / "unrelated-invalid.sh").write_text("if broken\n")
        with mock.patch.object(checker.shutil, "which", return_value=None):
            fields, detail = checker.check(self.directory)
        self.assertEqual(fields["pkgbase"], ["sample-bin"])
        self.assertIn("static checks", detail)

    def test_launcher_without_shell_extension_is_checked(self):
        self.payload.write_text("#!/usr/bin/bash\nif broken\n")
        old = repo_lib.read_srcinfo(self.directory / ".SRCINFO")["sha256sums"][0]
        new = hashlib.sha256(self.payload.read_bytes()).hexdigest()
        (self.directory / ".SRCINFO").write_text(self.srcinfo.replace(old, new))
        real_run = checker.subprocess.run
        def quiet_run(*args, **kwargs):
            return real_run(*args, capture_output=True, **kwargs)
        with mock.patch.object(checker.subprocess, "run", side_effect=quiet_run):
            with self.assertRaises(checker.subprocess.CalledProcessError):
                checker.check(self.directory)


class ManifestTests(RecipeFixture):
    def test_matching_release_and_new_version(self):
        self.assertEqual(self.inspect()["status"], "current")
        newer = copy.deepcopy(self.manifest)
        newer["latest"] = "1.1"
        self.assertEqual(self.inspect(manifest=newer)["status"], "review-update")

    def test_same_version_artifact_change_is_rejected(self):
        changed = copy.deepcopy(self.manifest)
        changed["files"][0]["sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "checksum changed"):
            self.inspect(manifest=changed)

    def test_url_checksum_pair_is_checked_together(self):
        extra = (
            "\tsource_x86_64 = https://example.test/1.0/another.tar.gz\n"
            "\tsha256sums_x86_64 = " + "c" * 64 + "\n"
        )
        (self.directory / ".SRCINFO").write_text(self.srcinfo.replace("\npkgname = sample-bin", extra + "\npkgname = sample-bin"))
        changed = copy.deepcopy(self.manifest)
        changed["files"][0]["sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "checksum changed"):
            self.inspect(manifest=changed)

    def test_missing_upstream_architecture_is_rejected(self):
        missing = copy.deepcopy(self.manifest)
        missing["files"].pop()
        with self.assertRaisesRegex(ValueError, "expected one Linux arm64"):
            self.inspect(manifest=missing)

    def test_feed_must_cover_recipe_architectures(self):
        item = copy.deepcopy(self.item)
        del item["release_feed"]["architectures"]["aarch64"]
        with self.assertRaisesRegex(ValueError, "architectures differ"):
            self.inspect(item=item)

    def test_new_release_still_requires_valid_hash_and_https(self):
        for key, value in [("sha256", "SKIP"), ("url", "http://example.test/file")]:
            changed = copy.deepcopy(self.manifest)
            changed["latest"] = "1.1"
            changed["files"][0][key] = value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    self.inspect(manifest=changed)


class ExportTests(RecipeFixture):
    def test_existing_empty_destination_is_never_overwritten(self):
        destination = self.root / "export"
        destination.mkdir()
        with mock.patch.object(exporter, "generated_srcinfo", side_effect=AssertionError("must not invoke makepkg")):
            with self.assertRaisesRegex(ValueError, "already exists"):
                exporter.export(self.directory, destination)
        self.assertEqual(list(destination.iterdir()), [])

    def test_dangling_destination_link_is_never_overwritten(self):
        destination = self.root / "export"
        destination.symlink_to(self.root / "does-not-exist")
        with self.assertRaisesRegex(ValueError, "already exists"):
            exporter.export(self.directory, destination)
        self.assertTrue(destination.is_symlink())

    def test_stale_srcinfo_prevents_export_and_directory_creation(self):
        destination = self.root / "export"
        generated = self.srcinfo.replace("license = MIT", "license = BSD-3-Clause")
        with self.assertRaisesRegex(ValueError, "stale"):
            self.export(destination, generated)
        self.assertFalse(destination.exists())

    def test_export_contains_only_declared_recipe_inputs(self):
        (self.directory / "unrelated.tar.gz").write_bytes(b"not a real binary")
        destination = self.root / "export"
        self.export(destination)
        self.assertEqual({p.name for p in destination.iterdir()}, {"PKGBUILD", ".SRCINFO", "launcher"})

    def test_escaping_pkgbuild_is_rejected_before_makepkg(self):
        outside = self.root / "unreviewed"
        outside.write_text("echo must-not-run\n")
        recipe = self.directory / "PKGBUILD"
        recipe.unlink()
        recipe.symlink_to(outside)
        with mock.patch.object(exporter, "generated_srcinfo", side_effect=AssertionError("must not execute")):
            with self.assertRaisesRegex(ValueError, "escaping"):
                exporter.export(self.directory, self.root / "export")


if __name__ == "__main__":
    unittest.main()
