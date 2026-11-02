#!/usr/bin/env python3
"""Synthetic-only tests; never include raw btsnoop, MACs, LinkKeys or PINs."""
import unittest
from analyze_legacy_auth_trace import summarize


class TraceAnalyzerTests(unittest.TestCase):
    def test_no_matching_events(self):
        self.assertEqual(summarize(["ordinary unrelated syslog"])["classification"],
                         "NO_MATCHING_TRACE_EVENTS")

    def test_pin_pending_without_hci_completion(self):
        result = summarize(["RB_AUTH pin_route=ui_callback",
                            "RB_AUTH java_pin_ui_dispatch local_started=0 min16=0"])
        self.assertEqual(result["classification"], "NO_HCI_AUTH_COMPLETION")
        self.assertEqual(result["pin_routes_observed"], ["ui_callback"])

    def test_hci_failure_without_pin_evidence(self):
        result = summarize(["RB_AUTH hci_completion status=0x22 sec_state=1"])
        self.assertEqual(result["classification"], "HCI_FAILURE_PIN_PATH_UNKNOWN")
        self.assertEqual(result["raw_hci_status"], "0x22")

    def test_hci_failure_after_java_handoff_no_reply(self):
        result = summarize([
            "RB_AUTH pin_request state=0 disabled=0 preset=0 fixed=0 callback=1",
            "RB_AUTH pin_route=ui_callback",
            "RB_AUTH java_pin_ui_dispatch local_started=0 min16=0",
            "RB_AUTH hci_completion status=0x22",
        ])
        self.assertEqual(result["classification"], "PIN_HANDOFF_UNCONFIRMED")
        self.assertFalse(result["host_pin_reply_observed"])

    def test_hci_failure_after_host_accepted_pin(self):
        result = summarize(["RB_AUTH ui_pin_reply accepted=1 state=4",
                            "RB_AUTH hci_completion status=0x22"])
        self.assertEqual(result["classification"], "HCI_FAILURE_AFTER_HOST_PIN_REPLY")
        self.assertTrue(result["host_pin_reply_accepted"])

    def test_pin_rejected_not_equivalent_to_no_reply(self):
        result = summarize(["RB_AUTH ui_pin_reply accepted=0 state=4",
                            "RB_AUTH hci_completion status=0x22"])
        self.assertEqual(result["classification"],
                         "PIN_REPLY_REJECTED_WITH_HCI_FAILURE")

    def test_hci_success_not_wireless_gamepad_success(self):
        result = summarize(["RB_AUTH hci_completion status=0x00",
                            "RB_AUTH key_notification type=2"])
        self.assertEqual(result["classification"], "HCI_AUTH_REPORTED_SUCCESS")
        self.assertEqual(result["key_notification_events"], 1)
        self.assertNotIn("wireless_gamepad_connected", result)

    def test_multiple_pin_requests_ambiguous(self):
        result = summarize(["RB_AUTH pin_request state=0",
                            "RB_AUTH pin_request state=0",
                            "RB_AUTH hci_completion status=0x22"])
        self.assertEqual(result["classification"], "AMBIGUOUS_MULTIPLE_ATTEMPTS")
        self.assertTrue(result["multiple_attempts_ambiguous"])

    def test_multiple_hci_results_ambiguous(self):
        result = summarize(["RB_AUTH hci_completion status=0x22",
                            "RB_AUTH hci_completion status=0x00"])
        self.assertEqual(result["classification"], "AMBIGUOUS_MULTIPLE_ATTEMPTS")
        self.assertIsNone(result["raw_hci_status"])

    def test_key_known_not_a_crypto_proof(self):
        result = summarize(["RB_AUTH key_request known=1 state=0",
                            "RB_AUTH hci_completion status=0x22"])
        self.assertTrue(result["prior_link_key_reported_known"])
        self.assertEqual(result["classification"], "HCI_FAILURE_PIN_PATH_UNKNOWN")

    def test_fixed_pin_route_without_visible_ui(self):
        result = summarize(["RB_AUTH pin_route=fixed",
                            "RB_AUTH hci_completion status=0x22"])
        self.assertEqual(result["pin_routes_observed"], ["fixed"])
        self.assertEqual(result["classification"], "HCI_FAILURE_PIN_PATH_UNKNOWN")

    def test_name_pending_classified_as_unconfirmed(self):
        result = summarize(["RB_AUTH pin_route=name_pending",
                            "RB_AUTH hci_completion status=0x22"])
        self.assertEqual(result["classification"], "PIN_HANDOFF_UNCONFIRMED")

    def test_original_line_never_emitted(self):
        result = summarize([
            "BTM secret-PIN=DO_NOT_REPRINT MAC=DO_NOT_REPRINT "
            "RB_AUTH hci_completion status=0x22 metadata_extra=ABCD",
        ])
        serialized = str(result)
        self.assertNotIn("DO_NOT_REPRINT", serialized)
        self.assertNotIn("ABCD", serialized)
        self.assertEqual(result["raw_hci_status"], "0x22")


if __name__ == "__main__":
    unittest.main()
