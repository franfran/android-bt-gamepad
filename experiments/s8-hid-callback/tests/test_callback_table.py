import hashlib
import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

p=Path(__file__).resolve().parents[1]/"verify_callback_table.py"
spec=importlib.util.spec_from_file_location("callback",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def synthetic():
    b=bytearray(0x5000)
    b[:4]=b"\x7fELF"
    b[4:6]=b"\x01\x01"
    struct.pack_into("<H",b,18,40)
    struct.pack_into("<I",b,28,52)
    struct.pack_into("<HH",b,42,32,2)
    # Synthetic ELF sparse virtual range with minimal tiny VMA->file mappings
    for i,(vaddr,sz,offset) in enumerate(((0x27e000,0x1000,0x100),(0x5e5000,0x1000,0x2000))):
        struct.pack_into("<IIIIIIII",b,52+i*32,1,offset,vaddr,vaddr,sz,sz,4,0x1000)
    struct.pack_into("<I",b,0x100+0x820,0x366970)
    struct.pack_into("<I",b,0x100+0x828,0x366922)
    for i,x in enumerate(m.EXPECTED):
        struct.pack_into("<I",b,0x2000+0xd0+i*4,x)
    return bytes(b)

class TestCallback(unittest.TestCase):
    def test_exact_table_agrees_with_both_callers(self):
        raw=synthetic()
        with patch.object(m,"EXPECTED_SHA256",hashlib.sha256(raw).hexdigest()):
            result=m.analyze(raw)
        self.assertTrue(result["same_callback_table_both_psms"])
        self.assertEqual(result["first_callback"],"hidh_l2cif_connect_ind")
        self.assertEqual(result["callback_execution_at_runtime"],"UNVERIFIED")
        self.assertFalse(result["injection_authorized"])

    def test_wrong_pointer_fails_closed(self):
        raw=bytearray(synthetic())
        struct.pack_into("<I",raw,0x100+0x828,0)
        with patch.object(m,"EXPECTED_SHA256",hashlib.sha256(raw).hexdigest()):
            with self.assertRaisesRegex(ValueError,"CALLBACK_POINTER_NOT_SHARED"):
                m.analyze(bytes(raw))

    def test_entry_mismatch_fails_closed(self):
        raw=bytearray(synthetic())
        struct.pack_into("<I",raw,0x2000+0xd0,0)
        with patch.object(m,"EXPECTED_SHA256",hashlib.sha256(raw).hexdigest()):
            with self.assertRaisesRegex(ValueError,"CALLBACK_ENTRIES_CHANGED"):
                m.analyze(bytes(raw))

    def test_unexpected_binary_hash_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"M3_ELF_SHA256_MISMATCH"):
            m.analyze(synthetic())

if __name__=="__main__":
    unittest.main()
