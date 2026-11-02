"""Strict synthetic, host-only HCI 0x22 vs 0x05 regression tests."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from classify_sanitized_hci_timeout import classify


def sample(status=0x22, ms=30061, complete=True):
    return {"capture_complete": complete, "events": [
        {"elapsed_ms": 0, "kind": "connection_complete", "status": 0},
        {"elapsed_ms": 3, "kind": "authentication_requested"},
        {"elapsed_ms": 4, "kind": "link_key_request"},
        {"elapsed_ms": 5, "kind": "link_key_negative_reply"},
        {"elapsed_ms": 10, "kind": "pin_code_request"},
        {"elapsed_ms": 10 + ms, "kind": "authentication_complete", "status": status},
        {"elapsed_ms": 10 + ms + 1, "kind": "disconnection_complete", "status": status},
    ]}


class SanitizedHciTimeoutTests(unittest.TestCase):
    def test_all_four_historical_relative_timeouts(self):
        # Interval metadata only; these are not the original raw captures.
        for ms in (30061, 30061, 30067, 30063):
            with self.subTest(ms=ms):
                report = classify(sample(ms=ms))
                self.assertEqual("NO_PIN_HCI_REPLY_OBSERVED_THEN_LMP_TIMEOUT",
                                 report["classification"])
                self.assertEqual(ms, report["pin_to_auth_complete_ms"])
                self.assertEqual("0x22", report["hci_auth_status"])

    def test_0x05_is_not_lmp_timeout(self):
        self.assertEqual("AUTHENTICATION_FAILURE_STATUS_0X05",
                         classify(sample(status=0x05))["classification"])

    def test_0x00_is_success_not_pin_failure(self):
        self.assertEqual("HCI_AUTHENTICATION_REPORTED_SUCCESS",
                         classify(sample(status=0x00))["classification"])

    def test_no_reply_claim_not_allowed_for_incomplete_capture(self):
        self.assertEqual("INCOMPLETE_CAPTURE_NO_ABSENCE_CLAIM",
                         classify(sample(complete=False))["classification"])

    def test_hci_command_reply_then_timeout_does_not_prove_remote_acceptance(self):
        data = sample()
        data["events"].insert(-2, {"elapsed_ms": 11, "kind": "pin_code_reply"})
        report = classify(data)
        self.assertEqual("HCI_PIN_REPLY_OBSERVED_THEN_LMP_TIMEOUT",
                         report["classification"])
        self.assertTrue(report["pin_reply_hci_command_observed"])
        self.assertIn("not peer acceptance", report["caveat"])

    def test_negative_reply_before_timeout_is_distinct(self):
        data = sample()
        data["events"].insert(-2, {"elapsed_ms": 11, "kind": "pin_code_negative_reply"})
        report = classify(data)
        self.assertEqual("HCI_PIN_REPLY_OBSERVED_THEN_LMP_TIMEOUT",
                         report["classification"])
        self.assertTrue(report["pin_negative_reply_hci_command_observed"])

    def test_late_pin_reply_after_auth_completion_is_not_credit(self):
        data = sample()
        data["events"].insert(-1, {"elapsed_ms": 30072, "kind": "pin_code_reply"})
        self.assertEqual("AMBIGUOUS_HCI_WINDOW", classify(data)["classification"])

    def test_missing_connection_complete_is_ambiguous(self):
        data = sample()
        del data["events"][0]
        self.assertEqual("AMBIGUOUS_HCI_WINDOW", classify(data)["classification"])

    def test_multiple_pin_requests_ambiguous(self):
        data = sample()
        data["events"].insert(-2, {"elapsed_ms": 20, "kind": "pin_code_request"})
        self.assertEqual("AMBIGUOUS_HCI_WINDOW", classify(data)["classification"])

    def test_multiple_auth_completions_ambiguous(self):
        data = sample()
        data["events"].insert(-1, {"elapsed_ms": 30071, "kind": "authentication_complete", "status": 0x22})
        self.assertEqual("AMBIGUOUS_HCI_WINDOW", classify(data)["classification"])

    def test_reject_sensitive_payload_field(self):
        data = sample()
        data["events"][4]["pin_bytes"] = "PRIVATE_VALUE"
        with self.assertRaises(ValueError):
            classify(data)

    def test_reject_mac_field(self):
        data = sample()
        data["mac"] = "PRIVATE_VALUE"
        with self.assertRaises(ValueError):
            classify(data)

    def test_reject_absolute_timestamp(self):
        data = sample()
        data["events"][4]["timestamp"] = "PRIVATE_VALUE"
        with self.assertRaises(ValueError):
            classify(data)

    def test_reject_malformed_status(self):
        data = sample()
        data["events"][-2]["status"] = "0x22"
        with self.assertRaises(ValueError):
            classify(data)

    def test_reject_negative_and_boolean_time(self):
        for bad in (-1, True):
            data = sample()
            data["events"][0]["elapsed_ms"] = bad
            with self.assertRaises(ValueError):
                classify(data)

    def test_reject_out_of_order(self):
        data = sample()
        data["events"][4]["elapsed_ms"] = 0
        with self.assertRaises(ValueError):
            classify(data)

    def test_cli_no_raw_input_echo(self):
        with tempfile.TemporaryDirectory() as tempdir:
            script = Path(__file__).with_name("classify_sanitized_hci_timeout.py")
            data = Path(tempdir) / "case.json"
            value = sample()
            data.write_text(json.dumps(value), encoding="utf-8")
            ok = subprocess.run([sys.executable, str(script), str(data)],
                                text=True, capture_output=True, check=False)
            self.assertEqual(0, ok.returncode)
            self.assertIn("LMP_TIMEOUT", ok.stdout)
            value["private_address"] = "DO_NOT_ECHO"
            data.write_text(json.dumps(value), encoding="utf-8")
            bad = subprocess.run([sys.executable, str(script), str(data)],
                                 text=True, capture_output=True, check=False)
            self.assertEqual(2, bad.returncode)
            self.assertNotIn("DO_NOT_ECHO", bad.stdout + bad.stderr)


if __name__ == "__main__":
    unittest.main()
