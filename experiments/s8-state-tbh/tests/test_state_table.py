import hashlib
import importlib.util
from pathlib import Path
import struct
import unittest
p=Path(__file__).resolve().parents[1]/"verify_state_table.py"
s=importlib.util.spec_from_file_location("tbh",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def sample():
    data=bytearray(0x3000)
    data[:6]=b"\x7fELF\x01\x01";struct.pack_into("<H",data,18,40)
    struct.pack_into("<I",data,28,52);struct.pack_into("<HH",data,42,32,1)
    struct.pack_into("<IIIIIIII",data,52,1,0x100,0x286000,0,0x1000,0x1000,5,0x1000)
    off=lambda addr:0x100+addr-0x286000
    data[off(m.TBH_ADDR):off(m.TBH_ADDR)+4]=bytes.fromhex("dfe810f0")
    for i,target in enumerate(m.EXPECTED):
        struct.pack_into("<H",data,off(m.TABLE_ADDR)+i*2,(target-m.TABLE_ADDR)//2)
    return bytes(data)
class TestStateTBH(unittest.TestCase):
    def test_real_state_targets_synthetic_fixture(self):
        x=sample();r=m.verify(x,hashlib.sha256(x).hexdigest())
        self.assertEqual([z["destination"] for z in r["states"]],[hex(v) for v in m.EXPECTED])
        self.assertEqual(r["event_to_state_mapping"],"UNVERIFIED")
        self.assertFalse(r["injection_authorized"])
    def test_hash_guard(self):
        with self.assertRaisesRegex(ValueError,"SHA256"):m.verify(sample())
    def test_opcode_guard(self):
        x=bytearray(sample()); x[0x100+m.TBH_ADDR-0x286000]=0
        with self.assertRaisesRegex(ValueError,"TBH_OPCODE"):m.verify(x,hashlib.sha256(x).hexdigest())
    def test_dispatch_entry_guard(self):
        x=bytearray(sample());x[0x100+m.TABLE_ADDR-0x286000]=0
        with self.assertRaisesRegex(ValueError,"STATE_TARGETS"):m.verify(x,hashlib.sha256(x).hexdigest())
if __name__=="__main__": unittest.main()
