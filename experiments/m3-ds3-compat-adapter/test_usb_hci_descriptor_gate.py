"""Synthetic, host-only tests for USB HCI descriptor classification.

No real USB enumeration or HCI controller operations.
"""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from usb_hci_descriptor_gate import inspect_descriptor


def valid():
    return {"interfaces": [{
        "number": 0,
        "alternate": 0,
        "class": 0xE0,
        "subclass": 1,
        "protocol": 1,
        "endpoints": [
            {"address": 0x83, "type": "interrupt"},
            {"address": 0x84, "type": "bulk"},
            {"address": 0x05, "type": "bulk"},
        ],
    }]}


class UsbHciDescriptorGateTests(unittest.TestCase):
    def assert_rejected(self, doc):
        code, _reason = inspect_descriptor(doc)
        self.assertEqual("NO_GO", code)

    def test_standard_shape_is_candidate_not_go(self):
        code, reason = inspect_descriptor(valid())
        self.assertEqual("DESCRIPTOR_CANDIDATE_ONLY", code)
        self.assertIn("UNTESTED", reason)

    def test_endpoint_addresses_not_fixed_to_example(self):
        self.assertEqual("DESCRIPTOR_CANDIDATE_ONLY", inspect_descriptor(valid())[0])

    def test_no_hci_interface(self):
        self.assert_rejected({"interfaces": []})

    def test_vendor_specific_interface_does_not_claim_standard_support(self):
        d = valid()
        d["interfaces"][0]["class"] = 0xFF
        self.assert_rejected(d)

    def test_ble_alternate_protocol_not_assumed_classic(self):
        d = valid()
        d["interfaces"][0]["protocol"] = 4
        self.assert_rejected(d)

    def test_interrupt_endpoint_missing(self):
        d = valid()
        d["interfaces"][0]["endpoints"].pop(0)
        self.assert_rejected(d)

    def test_bulk_out_direction_required(self):
        d = valid()
        d["interfaces"][0]["endpoints"][-1]["address"] = 0x85
        self.assert_rejected(d)

    def test_duplicate_endpoint_address_rejected(self):
        d = valid()
        d["interfaces"][0]["endpoints"][1]["address"] = 0x83
        self.assert_rejected(d)

    def test_only_alt_one_rejected(self):
        d = valid()
        d["interfaces"][0]["alternate"] = 1
        self.assert_rejected(d)

    def test_ambiguous_multiple_hci_interfaces_rejected(self):
        d = valid()
        other = copy.deepcopy(d["interfaces"][0])
        other["number"] = 1
        d["interfaces"].append(other)
        self.assert_rejected(d)

    def test_unrelated_hid_interface_does_not_block_class_match(self):
        d = valid()
        d["interfaces"].append({
            "number": 1, "alternate": 0, "class": 3, "subclass": 1, "protocol": 1,
            "endpoints": [{"address": 0x87, "type": "interrupt"}]
        })
        self.assertEqual("DESCRIPTOR_CANDIDATE_ONLY", inspect_descriptor(d)[0])

    def test_no_private_ids_in_json_input(self):
        d = valid()
        d["serial"] = "DO_NOT_LOG"
        self.assert_rejected(d)

    def test_reject_bool_or_out_of_range_addresses(self):
        for bad in (True, 256, -1, 0x80, 0):
            d = valid()
            d["interfaces"][0]["endpoints"][0]["address"] = bad
            self.assert_rejected(d)

    def test_cli_is_offline_and_does_not_echo_private_fields(self):
        script = pathlib.Path(__file__).with_name("usb_hci_descriptor_gate.py")
        with tempfile.TemporaryDirectory() as tmp:
            data = pathlib.Path(tmp) / "descriptor.json"
            data.write_text(json.dumps(valid()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(script), str(data)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("DESCRIPTOR_CANDIDATE_ONLY", result.stdout)
            d = valid()
            d["serial"] = "DO_NOT_LOG"
            data.write_text(json.dumps(d), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(script), str(data)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(1, result.returncode)
            self.assertNotIn("DO_NOT_LOG", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
