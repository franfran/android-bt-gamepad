import hashlib,importlib.util,struct
from pathlib import Path
import unittest
path=Path(__file__).resolve().parents[1]/"verify_route.py"
spec=importlib.util.spec_from_file_location("verify_route",path)
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
BASE=0x286000
def fixture():
    data=bytearray(0x3d000)
    data[:6]=b"\x7fELF\x01\x01"
    struct.pack_into("<H",data,18,40)
    struct.pack_into("<I",data,28,52)
    struct.pack_into("<HH",data,42,32,1)
    struct.pack_into("<IIIIIIII",data,52,1,0x100,BASE,0,0x3c000,0x3c000,5,0x1000)
    def write(addr,b):data[0x100+addr-BASE:0x100+addr-BASE+len(b)]=b
    for addr,hx in v.CHECKS.items():write(addr,bytes.fromhex(hx))
    write(0x2861d2,struct.pack("<H",(0x2861e4-0x2861d2)//2))
    write(0x286d0e+20,struct.pack("<H",(0x288670-0x286d0e)//2))
    return bytes(data)
class RouteTests(unittest.TestCase):
    def test_state0_event10_security_path(self):
        data=fixture()
        out=v.verify(data,hashlib.sha256(data).hexdigest())
        self.assertEqual(out["event_target"],"0x288670")
        self.assertEqual(out["classic_security_call"],"0x2897b4")
        self.assertEqual(out["actual_ds3_runtime_path"],"UNVERIFIED")
        self.assertFalse(out["injection_authorized"])
    def test_strict_provenance(self):
        with self.assertRaisesRegex(ValueError,"ELF_SHA"):v.verify(fixture())
    def test_altered_event_target_rejected(self):
        data=bytearray(fixture())
        struct.pack_into("<H",data,0x100+0x286d0e+20-BASE,1)
        with self.assertRaisesRegex(ValueError,"DISPATCH_MISMATCH"):
            v.verify(bytes(data),hashlib.sha256(data).hexdigest())
    def test_altered_security_instruction_rejected(self):
        data=bytearray(fixture());data[0x100+0x2897b4-BASE]=0
        with self.assertRaisesRegex(ValueError,"MISMATCH_AT"):
            v.verify(bytes(data),hashlib.sha256(data).hexdigest())
if __name__=="__main__":unittest.main()
