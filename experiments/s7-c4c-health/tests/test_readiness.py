import importlib.util
import io
import json
import pathlib
import subprocess
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "read-only-readiness.py"
spec = importlib.util.spec_from_file_location("readiness", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

HEALTH = {"identity_verified": True, "tracer_absent": True, "threads": 48}


class ReadinessTests(unittest.TestCase):
    def test_wifi_primary_alternate_present_but_still_no_go(self):
        inventory = {"192.0.2.1:1080": "device", "USB_ID": "device"}
        with patch.object(mod, "adb_inventory", return_value=inventory), \
             patch.object(mod.HEALTH, "collect", return_value=HEALTH):
            result = mod.readiness("192.0.2.1:1080")
        self.assertEqual(result["primary_transport"], "wifi_adb")
        self.assertTrue(result["alternate_adb_device_enumerated"])
        self.assertFalse(result["injection_authorized"])
        self.assertFalse(result["recovery_action_executed"])
        self.assertEqual(result["transport_survival_during_bluetooth_failure"], "UNVERIFIED")
        self.assertEqual(result["decision"], "NO_GO")
        self.assertNotIn("192.0.2.", json.dumps(result))
        self.assertNotIn("USB_ID", json.dumps(result))

    def test_missing_transport_fails_closed_before_device_inspection(self):
        with patch.object(mod, "adb_inventory", return_value={"net": "unauthorized"}), \
             patch.object(mod.HEALTH, "collect") as collect:
            with self.assertRaisesRegex(RuntimeError, "not ready"):
                mod.readiness("net")
            collect.assert_not_called()

    def test_no_alternate_does_not_imply_usb(self):
        with patch.object(mod, "adb_inventory", return_value={"USB_ID": "device"}), \
             patch.object(mod.HEALTH, "collect", return_value=HEALTH):
            result = mod.readiness("USB_ID")
        self.assertEqual(result["primary_transport"], "usb_or_local_adb")
        self.assertFalse(result["alternate_adb_device_enumerated"])
        self.assertEqual(result["usb_fallback_owner_confirmed"], "REPORTED_SEPARATELY")

    def test_ambiguous_health_fails_closed(self):
        with patch.object(mod, "adb_inventory", return_value={"net": "device"}), \
             patch.object(mod.HEALTH, "collect",
                          return_value={"identity_verified": False, "tracer_absent": True}):
            with self.assertRaises(RuntimeError):
                mod.readiness("net")

    def test_failed_inventory_only_safe_errors(self):
        fake = subprocess.CompletedProcess(args=[], returncode=1, stdout=b"", stderr=b"secret")
        with patch.object(mod.subprocess, "run", return_value=fake):
            with self.assertRaisesRegex(RuntimeError, "inventory unavailable") as ctx:
                mod.adb_inventory()
            self.assertNotIn("secret", str(ctx.exception))

    def test_source_has_no_bluetooth_mutation(self):
        code = SCRIPT.read_text()
        for command in ("kill -9", "setprop ", "am force-stop", "svc bluetooth",
                        "PTRACE_ATTACH", "service call bluetooth", "adb reboot"):
            self.assertNotIn(command, code)


if __name__ == "__main__":
    unittest.main()
