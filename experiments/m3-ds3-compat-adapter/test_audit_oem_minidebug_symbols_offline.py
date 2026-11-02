"""Host-only synthetic tests; NO private M3 binaries or device operations."""
import hashlib
import lzma
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import audit_oem_minidebug_symbols_offline as gate


def elf32_arm(sections):
    names = b"\0.shstrtab\0" + b"".join(n.encode() + b"\0" for n, _ in sections)
    offsets = {".shstrtab": 1}
    cursor = len(b"\0.shstrtab\0")
    for name, _ in sections:
        offsets[name] = cursor
        cursor += len(name) + 1
    data = bytearray(52)
    data[:4] = b"\x7fELF"
    data[4:6] = b"\x01\x01"
    struct.pack_into("<H", data, 18, 40)
    positions = {}
    for name, payload in [(".shstrtab", names), *sections]:
        positions[name] = (len(data), len(payload))
        data.extend(payload)
    section_table = len(data)
    data.extend(b"\0" * 40)
    for name in [".shstrtab", *(n for n, _ in sections)]:
        entry = bytearray(40)
        location, length = positions[name]
        struct.pack_into("<II", entry, 0, offsets[name], 3 if name == ".shstrtab" else 1)
        struct.pack_into("<II", entry, 16, location, length)
        data.extend(entry)
    struct.pack_into("<I", data, 32, section_table)
    struct.pack_into("<HHH", data, 46, 40, 2 + len(sections), 1)
    return bytes(data)


class MinidebugPluginGateTests(unittest.TestCase):
    def test_minidebug_xz_roundtrip(self):
        inner = elf32_arm([])
        outer = elf32_arm([(".gnu_debugdata", lzma.compress(inner))])
        self.assertEqual(inner, gate.unpack_minidebug(gate.section(outer, ".gnu_debugdata")))

    def test_missing_section_rejected(self):
        with self.assertRaisesRegex(ValueError, "no original"):
            gate.section(elf32_arm([]), ".gnu_debugdata")

    def test_wrong_machine_rejected(self):
        b = bytearray(elf32_arm([]))
        struct.pack_into("<H", b, 18, 62)
        with self.assertRaisesRegex(ValueError, "ARM"):
            gate.section(b, ".gnu_debugdata")

    def test_corrupt_compression_rejected(self):
        with self.assertRaises((ValueError, lzma.LZMAError)):
            gate.unpack_minidebug(b"BAD")

    def test_non_elf_minidebug_rejected(self):
        with self.assertRaisesRegex(ValueError, "not ELF"):
            gate.unpack_minidebug(lzma.compress(b"not ELF here"))

    def test_only_allowlisted_symbol_names_public(self):
        symbols = (
            "1: 00000000 0 FUNC LOCAL DEFAULT 2 hidh_conn_reg\n"
            "2: 00000000 0 FUNC LOCAL DEFAULT 2 PRIVATE_NAME\n"
            "3: 00000000 0 FUNC LOCAL DEFAULT 2 custom_plugin_register\n"
            "4: 00000000 0 FUNC GLOBAL DEFAULT UND dlopen\n"
        )
        result = gate.allowed_symbol_evidence(symbols)
        self.assertEqual(["hidh_conn_reg"], result["exact_allowlisted_defined_symbols"])
        self.assertEqual(1, result["other_symbol_names_with_plugin_like_tokens_count"])
        self.assertNotIn("custom_plugin_register", str(result))
        self.assertNotIn("PRIVATE_NAME", str(result))

    def test_repeated_candidate_deduplicated(self):
        result = gate.allowed_symbol_evidence(
            "1: 0 0 FUNC LOCAL DEFAULT 2 custom_plugin\n"
            "2: 0 0 FUNC LOCAL DEFAULT 2 custom_plugin\n")
        self.assertEqual(1, result["other_symbol_names_with_plugin_like_tokens_count"])

    def test_sha_mismatch_no_readelf_or_minidebug(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "fake.o"
            file.write_bytes(elf32_arm([]))
            with patch.object(gate.subprocess, "run", side_effect=AssertionError):
                with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                    gate.audit(file)

    def test_valid_synthetic_metadata_does_not_claim_plugin(self):
        inner = elf32_arm([])
        outer = elf32_arm([(".gnu_debugdata", lzma.compress(inner))])
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "test.o"
            file.write_bytes(outer)
            from types import SimpleNamespace
            with patch.object(gate.subprocess, "run", return_value=SimpleNamespace(
                    returncode=0, stdout="Build ID: " + gate.BUILD_ID_2024)):
                with patch.object(gate, "run_readelf", return_value=(
                        "1: 0 1 FUNC LOCAL DEFAULT 2 hidh_conn_reg")):
                    result = gate.audit(file, hashlib.sha256(outer).hexdigest())
        self.assertTrue(result["mini_debug_extracted_and_parsed"])
        self.assertIn("UNRESOLVED", result["decision"])


if __name__ == "__main__":
    unittest.main()
