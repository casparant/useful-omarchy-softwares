"""Configured hook evidence and the cosh application entry."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("control_entry", ROOT / "agent_entry.py")
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
aw = entry._aw


def configuration():
    return {"spec": {"events": {
        "tool.before": {"enabled": True, "steps": [
            {"provider": "security", "operation": "scan_code", "on_error": "block"},
            {"provider": "tokenless", "operation": "pre_tool", "on_error": "report"},
        ]},
        "tool.after": {"enabled": True, "steps": [
            {"provider": "security", "operation": "observe_tool", "on_error": "report"},
            {"provider": "tokenless", "operation": "post_tool", "on_error": "report"},
        ]},
    }}}


class ControlPlaneTest(unittest.TestCase):
    def test_before_and_after_keep_order_and_error_behavior(self):
        original = configuration()
        previous = copy.deepcopy(original)
        result = aw.hook_plan(original, "security", "tokenless")
        self.assertEqual(original, previous)
        self.assertEqual(result["status"], "configured")
        self.assertEqual([[s["role"] for s in p["steps"]] for p in result["phases"]],
                         [["security", "optimization"], ["observation", "compression"]])
        self.assertEqual(result["phases"][0]["steps"][0]["on_error"], "block")
        self.assertNotIn("adopted", json.dumps(result))
        self.assertNotIn("session", json.dumps(result))

    def test_custom_disabled_conditional_steps_are_not_hidden(self):
        value = configuration()
        before = value["spec"]["events"]["tool.before"]
        before["enabled"] = False
        before["match"] = {"tools": ["PRIVATE_TOOL"]}
        before["steps"].insert(1, {
            "provider": "PRIVATE_CUSTOM_PROVIDER", "on_error": "block", "enabled": False,
            "native": {"command": "PRIVATE_COMMAND"},
        })
        result = aw.hook_plan(value, "security", "tokenless")
        phase = result["phases"][0]
        self.assertFalse(phase["enabled"])
        self.assertTrue(phase["conditional"])
        self.assertEqual(phase["steps"][1], {"role": "custom", "on_error": "block", "enabled": False})
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertEqual(phase["steps"][2]["role"], "optimization")

    def test_contract_supports_withholding_and_all_128_steps(self):
        value = configuration()
        after = value["spec"]["events"]["tool.after"]
        after["steps"][1]["on_error"] = "withhold_result"
        after["steps"] *= 64
        self.assertEqual(len(aw.hook_plan(value, "security", "tokenless")["phases"][1]["steps"]), 128)
        after["steps"].append(after["steps"][0])
        with self.assertRaises(ValueError):
            aw.hook_plan(value, "security", "tokenless")

    def test_missing_or_malformed_plan_cannot_become_an_active_chain(self):
        for mutate in [
            lambda v: v["spec"]["events"]["tool.before"].pop("enabled"),
            lambda v: v["spec"]["events"]["tool.before"]["steps"][0].pop("on_error"),
            lambda v: v["spec"]["events"]["tool.before"]["steps"][0].update(enabled="yes"),
        ]:
            value = configuration()
            mutate(value)
            with self.assertRaises((ValueError, KeyError)):
                aw.hook_plan(value, "security", "tokenless")
        self.assertEqual(aw.empty("query_failed")["hook_plan"]["phases"], [])

    def test_absent_events_are_explicitly_unconfigured(self):
        result = aw.hook_plan({"spec": {"events": {}}}, None, None)
        self.assertTrue(all(not p["enabled"] and not p["steps"] for p in result["phases"]))

    def test_known_operation_on_an_unknown_provider_stays_custom(self):
        value = configuration()
        result = aw.hook_plan(value, None, None)
        self.assertTrue(all(s["role"] == "custom" for p in result["phases"] for s in p["steps"]))

    def test_cosh_discovery_prefers_public_entry_and_accepts_shell_binary(self):
        with patch.object(entry, "language_settings", return_value={"language": "en"}):
            cosh = next(item for item in entry.catalog() if item["id"] == "cosh")
        for available, expected in [
            ({"cosh": "/usr/bin/cosh", "cosh-shell": "/usr/bin/cosh-shell"}, "/usr/bin/cosh"),
            ({"cosh-shell": "/usr/bin/cosh-shell"}, "/usr/bin/cosh-shell"),
            ({}, None),
        ]:
            with patch.object(entry, "which", side_effect=available.get):
                self.assertEqual(entry.command_for(cosh), [expected] if expected else None)


if __name__ == "__main__":
    unittest.main()
