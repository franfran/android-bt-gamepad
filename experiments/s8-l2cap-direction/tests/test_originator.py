import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/"audit_originator.py"
sp=importlib.util.spec_from_file_location("direction",p)
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def fixture():
    out=[]
    for site,(mov,val) in m.EXPECTED.items():
        out.append(f"  {mov:06x}: 220{val}          movs r2, #0x{val:x}")
        out.append(f"  {site:06x}: f7cf fabc     bl 0x258e68 <symbol>")
    return "\n".join(out)
class Tests(unittest.TestCase):
    def test_five_callsite_directions(self):
        result=m.audit(fixture())
        self.assertEqual(result["incoming_direction_candidates"],["0x286ea8","0x2897b4"])
        self.assertEqual(len(result["outgoing_direction_callsites"]),3)
        self.assertEqual(result["runtime_event_selection"],"UNVERIFIED")
    def test_wrong_flag_rejected(self):
        with self.assertRaises(ValueError):
            m.audit(fixture().replace("movs r2, #0x0","movs r2, #0x1",1))
    def test_missing_callsite_rejected(self):
        with self.assertRaises(ValueError):
            m.audit("\n".join(fixture().splitlines()[:-1]))
if __name__=="__main__":unittest.main()
