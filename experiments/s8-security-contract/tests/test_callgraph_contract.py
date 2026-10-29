import importlib.util
from pathlib import Path
import unittest

module_path=Path(__file__).resolve().parents[1]/"callgraph_contract.py"
spec=importlib.util.spec_from_file_location("contract",module_path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

SOURCE=(Path(__file__).resolve().parents[3]/
        "research/retrobox-stage3c-callgraph.txt").read_text()

class TestContract(unittest.TestCase):
    def test_existing_evidence(self):
        result=m.audit(SOURCE)
        self.assertEqual(result["verified_edges"],6)
        self.assertEqual(result["hid_to_l2cap_security_dispatch"],"UNVERIFIED")
        self.assertEqual(result["runtime_gd_or_legacy_branch"],"UNVERIFIED")
        self.assertEqual(result["decision"],"NO_GO")
        self.assertFalse(result["injection_authorized"])

    def test_deleted_edge_fails_closed(self):
        altered=SOURCE.replace("0x258b5a bl  0x257c04","0x258b5a bl  0x257c05")
        with self.assertRaises(ValueError):
            m.audit(altered)

    def test_removed_function_fails_closed(self):
        altered=SOURCE.replace("FUNCTION _Z13hidh_conn_regv:", "FUNCTION absent:")
        with self.assertRaises(ValueError):
            m.audit(altered)

    def test_hid_callback_unresolved_not_claimed_link(self):
        result=m.audit(SOURCE)
        record=next(x for x in result["checked_functions"] if "connect_ind" in x["symbol"])
        self.assertGreater(record["indirect_or_unresolved_calls"],0)
        self.assertEqual(result["hid_callback_to_btm_auth"],"UNVERIFIED")

if __name__=="__main__":
    unittest.main()
