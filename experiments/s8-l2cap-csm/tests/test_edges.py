import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/"audit_security_edges.py"
spec=importlib.util.spec_from_file_location("audit",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def fixture():
    return "\n".join(f"  {site:06x}: f7d1 ffde     bl 0x{target:x} <named>" for site,target in m.EXPECTED.items())
class Tests(unittest.TestCase):
    def test_seven_validated_direct_edges(self):
        out=m.audit(fixture())
        self.assertEqual(out["verified_direct_edges"],7)
        self.assertEqual(out["incoming_ds3_state_selection"],"UNVERIFIED")
        self.assertFalse(out["injection_authorized"])
    def test_missing_edge_rejected(self):
        with self.assertRaises(ValueError):m.audit(fixture().splitlines()[1])
    def test_changed_edge_rejected(self):
        with self.assertRaises(ValueError):m.audit(fixture().replace("0x258e68","0x258e69",1))
    def test_duplicate_edge_rejected(self):
        with self.assertRaises(ValueError):m.audit(fixture()+"\n"+fixture().splitlines()[0])
if __name__=="__main__":unittest.main()
