import importlib.util
from pathlib import Path
import unittest
file=Path(__file__).resolve().parents[1]/"audit_pending_branch.py"
sp=importlib.util.spec_from_file_location("audit_pending",file)
m=importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)
def fixture():
    return "\n".join(f"  {k:x}: f7ff ffff  {op} {args}" for k,(op,args) in m.EXPECTED.items())
class TestPending(unittest.TestCase):
    def test_verified_branch(self):
        r=m.audit(fixture())
        self.assertEqual(r["verified"],10)
        self.assertEqual(r["ds3_runtime_path"],"UNVERIFIED")
        self.assertEqual(r["decision"],"NO_GO")
    def test_changed_psm_rejected(self):
        with self.assertRaises(ValueError):
            m.audit(fixture().replace("r1, [r1, #0x2]","r1, [r1, #0x4]"))
    def test_changed_pending_response_rejected(self):
        with self.assertRaises(ValueError):
            m.audit(fixture().replace("bl 0x290f98","bl 0x290f99"))
    def test_missing_branch_rejected(self):
        with self.assertRaises(ValueError):
            m.audit("\n".join(fixture().splitlines()[1:]))
if __name__=="__main__":
    unittest.main()
