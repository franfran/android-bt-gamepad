import gzip
import struct
import unittest
from audit_uhid_support import native_summary, kernel_config_summary
from test_elf32_symbols import fixture


def elf32(payload=b""):
    data = bytearray(52)
    data[:6] = b"\x7fELF\x01\x01"
    struct.pack_into("<H", data, 18, 40)
    return bytes(data) + payload


class AuditTests(unittest.TestCase):
    def test_legacy_negative_marker_is_clue_not_proof(self):
        result = native_summary(elf32(b"UHID_SET_REPORT_REPLY not supported"))
        self.assertTrue(result["literal_markers"]["legacy_no_set_report_reply"])
        self.assertEqual(result["result"], "INCONCLUSIVE_BINARY_MARKERS_ONLY")

    def test_absent_marker_never_claims_support(self):
        result = native_summary(elf32())
        self.assertFalse(result["literal_markers"]["uhid_set_report_label"])
        self.assertEqual(result["result"], "INCONCLUSIVE_BINARY_MARKERS_ONLY")

    def test_wrong_architecture_rejected(self):
        x = bytearray(elf32())
        struct.pack_into("<H", x, 18, 62)
        with self.assertRaisesRegex(ValueError, "ARM"):
            native_summary(bytes(x))

    def test_sha_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            native_summary(elf32(), expected_sha256="0"*64)

    def test_thumb_symbol_json_uses_actual_instruction_offset(self):
        report = native_summary(fixture(thumb=True))
        symbols = report["candidate_function_symbols"]
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0]["symbol_value"], "0x1201")
        self.assertEqual(symbols[0]["instruction_vma"], "0x1200")
        self.assertEqual(symbols[0]["file_offset"], "0x200")
        self.assertTrue(symbols[0]["thumb"])

    def test_kernel_config_plain_and_unknown(self):
        r = kernel_config_summary(b"CONFIG_UHID=y\n# CONFIG_HID_SONY is not set\n")
        self.assertEqual(r["config"], {
            "CONFIG_HID": "UNKNOWN", "CONFIG_UHID": "y", "CONFIG_HID_SONY": "n"
        })

    def test_kernel_config_gzip(self):
        r = kernel_config_summary(gzip.compress(b"CONFIG_HID=y\nCONFIG_HID_SONY=m\n"))
        self.assertEqual(r["config"]["CONFIG_HID_SONY"], "m")


if __name__ == "__main__":
    unittest.main()
