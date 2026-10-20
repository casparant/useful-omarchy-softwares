"""Protect the packaged receipt boundary against mutation and mixed builds."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from aw_verify import COMPONENTS, verify_receipts


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.prefix = Path(self.temporary.name)
        directory = self.prefix / ".aw-packages"
        directory.mkdir()
        for name in COMPONENTS:
            target = self.prefix / name
            target.write_bytes(b"executable fixture")
            target.chmod(0o755)
            value = {"component": name, "source_commit": "a" * 40,
                     "version": "0.1.0-preview.1", "arch": "aarch64", "os": "linux",
                     "requires": {} if name == "aw-core" else {"aw-core": "0.1.0-preview.1"},
                     "files": {name: {"sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "mode": 0o755}}}
            (directory / (name + ".json")).write_text(json.dumps(value))

    def change(self, component, mutate):
        path = self.prefix / ".aw-packages" / (component + ".json")
        value = json.loads(path.read_text())
        mutate(value)
        path.write_text(json.dumps(value))

    def test_matching_receipts_pass(self):
        self.assertEqual(set(verify_receipts(self.prefix)), COMPONENTS)

    def test_postprocessing_or_modified_binary_is_rejected(self):
        (self.prefix / "aw-provider-tokenless").write_bytes(b"stripped or changed")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            verify_receipts(self.prefix)

    def test_wrong_mode_is_rejected(self):
        (self.prefix / "aw-provider-sec-core").chmod(0o777)
        with self.assertRaisesRegex(ValueError, "mode mismatch"):
            verify_receipts(self.prefix)

    def test_mixed_source_build_is_rejected(self):
        self.change("aw-provider-sec-core", lambda value: value.update(source_commit="b" * 40))
        with self.assertRaisesRegex(ValueError, "provenance mismatch"):
            verify_receipts(self.prefix)

    def test_wrong_component_dependency_is_rejected(self):
        self.change("aw-provider-tokenless", lambda value: value.update(requires={"aw-core": "other"}))
        with self.assertRaisesRegex(ValueError, "dependency mismatch"):
            verify_receipts(self.prefix)

    def test_missing_component_is_rejected(self):
        (self.prefix / ".aw-packages/aw-provider-sec-core.json").unlink()
        with self.assertRaisesRegex(ValueError, "missing component"):
            verify_receipts(self.prefix)

    def test_payload_link_is_rejected(self):
        target = self.prefix / "aw-provider-tokenless"
        target.unlink()
        target.symlink_to(self.prefix / "aw-core")
        with self.assertRaisesRegex(ValueError, "linked payload"):
            verify_receipts(self.prefix)

    def test_escaping_receipt_path_is_rejected(self):
        def mutate(value):
            value["files"] = {"../outside": next(iter(value["files"].values()))}
        self.change("aw-core", mutate)
        with self.assertRaisesRegex(ValueError, "invalid or duplicate"):
            verify_receipts(self.prefix)


if __name__ == "__main__":
    unittest.main()
