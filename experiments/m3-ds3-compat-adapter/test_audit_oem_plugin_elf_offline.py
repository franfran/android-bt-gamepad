"""Host-only synthetic tests for a fail-closed OEM ELF metadata inventory.

No proprietary binaries or Android/BT device operations.
"""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import audit_oem_plugin_elf_offline as target


def fake_arm32():
    data = bytearray(52)
    data[:4] = b"\x7fELF"
    data[4] = data[5] = 1
    struct.pack_into("<H", data, 18, 40)
    return bytes(data)


class ElfAuditTests(unittest.TestCase):
    def test_valid_arm32(self):
        self.assertEqual("ARM", target.elf_arm32_header(fake_arm32())["machine"])

    def test_elf64_rejected(self):
        data = bytearray(fake_arm32())
        data[4] = 2
        with self.assertRaises(ValueError):
            target.elf_arm32_header(data)

    def test_big_endian_rejected(self):
        data = bytearray(fake_arm32())
        data[5] = 2
        with self.assertRaises(ValueError):
            target.elf_arm32_header(data)

    def test_non_arm_rejected(self):
        data = bytearray(fake_arm32())
        struct.pack_into("<H", data, 18, 62)
        with self.assertRaises(ValueError):
            target.elf_arm32_header(data)

    def test_bad_magic_rejected(self):
        with self.assertRaises(ValueError):
            target.elf_arm32_header(bytes(52))

    def test_dynamic_needed(self):
        sample = """
 0x00000001 (NEEDED) Shared library: [libc.so]
 0x00000001 (NEEDED) Shared library: [libdl.so]
 0x0000000e (SONAME) Library soname: [libbluetooth.so]
"""
        self.assertEqual((["libc.so", "libdl.so"], ["libbluetooth.so"]),
                         target.parse_dynamic(sample))

    def test_duplicate_needed_deduplicated(self):
        s = " (NEEDED) Shared library: [libdl.so]"
        self.assertEqual(["libdl.so"], target.parse_dynamic(s + "\n" + s)[0])

    def test_symbol_import_export_filter(self):
        sample = """
 2: 00000000 0 FUNC GLOBAL DEFAULT UND dlopen
 3: 00000000 0 FUNC GLOBAL DEFAULT UND dlsym@LIBC
 4: 00000000 0 FUNC GLOBAL DEFAULT 19 btif_hh_get_interface
 5: 00000000 0 FUNC GLOBAL DEFAULT UND unrelated_symbol
"""
        self.assertEqual((["dlopen", "dlsym"], ["btif_hh_get_interface"]),
                         target.parse_symbol_table(sample))

    def test_build_id(self):
        self.assertEqual([target.OEM_2024_BUILD_ID],
                         target.parse_build_id("Build ID: " + target.OEM_2024_BUILD_ID))

    def test_no_build_id(self):
        self.assertEqual([], target.parse_build_id("no notes"))

    def test_library_basename_only(self):
        sample = "/vendor/lib/hw/libbt-vendor.so\n/system/lib/libbluetooth.so\nOTHER_TEXT"
        self.assertEqual(["libbluetooth.so", "libbt-vendor.so"],
                         target.find_library_mentions(sample))

    def test_arbitrary_nonlibrary_strings_ignored(self):
        self.assertEqual([], target.find_library_mentions("OTHER_TEXT\nMULTI_LINE_RECORD\n"))

    def test_sha_mismatch_stops_before_commands(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "test.elf"
            p.write_bytes(fake_arm32())
            with patch.object(target, "run_binutil", side_effect=AssertionError):
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    target.audit(p, target.OEM_2024_SHA256)

    def test_build_id_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "test.elf"
            content = fake_arm32()
            p.write_bytes(content)
            responses = iter([
                "(NEEDED) Shared library: [libdl.so]",
                " 2: 00000000 0 FUNC GLOBAL DEFAULT UND dlopen",
                "Build ID: deadbeefcafe1234",
                "libexample.so",
            ])
            with patch.object(target.shutil, "which", return_value="/usr/bin/readelf"), \
                 patch.object(target, "run_binutil", side_effect=lambda *_: next(responses)):
                with self.assertRaisesRegex(ValueError, "build-id mismatch"):
                    target.audit(p, hashlib.sha256(content).hexdigest())

    def test_positive_synthetic_still_unresolved(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "test.elf"
            content = fake_arm32()
            p.write_bytes(content)
            responses = iter([
                "(NEEDED) Shared library: [libdl.so]",
                " 2: 00000000 0 FUNC GLOBAL DEFAULT UND dlopen",
                "Build ID: " + target.OEM_2024_BUILD_ID,
                "UNRELATED_RECORD\nlibexample.so",
            ])
            with patch.object(target.shutil, "which", return_value="/usr/bin/readelf"), \
                 patch.object(target, "run_binutil", side_effect=lambda *_: next(responses)):
                report = target.audit(p, hashlib.sha256(content).hexdigest())
            self.assertIn("UNRESOLVED", report["plugin_decision"])
            self.assertIn("libexample.so", report["embedded_library_basename_mentions"])
            self.assertNotIn("UNRELATED_RECORD", json.dumps(report))

    def test_cli_sha_mismatch_fails_without_path_echo(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "test.elf"
            p.write_bytes(fake_arm32())
            proc = subprocess.run(
                [sys.executable, str(Path(__file__).with_name(
                    "audit_oem_plugin_elf_offline.py")), str(p)],
                capture_output=True, text=True,
            )
            self.assertEqual(2, proc.returncode)
            self.assertNotIn(str(p), proc.stdout + proc.stderr)

    def test_cli_missing_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "not-present.elf"
            proc = subprocess.run(
                [sys.executable, str(Path(__file__).with_name(
                    "audit_oem_plugin_elf_offline.py")), str(p)],
                capture_output=True, text=True,
            )
            self.assertEqual(2, proc.returncode)
            self.assertNotIn(str(p), proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
