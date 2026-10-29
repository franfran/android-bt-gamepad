import importlib.util
from pathlib import Path
import unittest

root=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location("inspect_dispatch",Path(__file__).resolve().parents[1]/"inspect_dispatch.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
source=(root/"research/retrobox-stage3c-callgraph.txt").read_text()

class Tests(unittest.TestCase):
    def test_archived_callback_targets(self):
        result=m.inspect(source)
        targets={x["target_vma"] for x in result["candidates"]}
        self.assertTrue({"0x5dee60","0x5deea0","0x5df050"}.issubset(targets))
        self.assertEqual(result["callback_resolution"],"UNVERIFIED")
        self.assertFalse(result["security_path_proven"])
        self.assertFalse(result["injection_authorized"])

    def test_deduplicates_targets(self):
        result=m.candidates(source)
        self.assertEqual(len({x["target_vma"] for x in result}),len(result))
        repeated=[x for x in result if x["target_vma"]=="0x5deea0"][0]
        self.assertGreaterEqual(len(repeated["callsite_vmas"]),2)

    def test_outside_function_not_attributed(self):
        other="FUNCTION other: 0x27ee28 size=720\n  0x27ef1e blx 0x5df050 -> unresolved"
        self.assertEqual(m.candidates(other),[])

    def test_missing_evidence_fails_closed(self):
        with self.assertRaises(ValueError):
            m.inspect("FUNCTION none: 0x0 size=0")

if __name__=="__main__":
    unittest.main()
