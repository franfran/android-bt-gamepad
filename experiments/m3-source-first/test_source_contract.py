import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("check_bta_source_contract", HERE / "check_bta_source_contract.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class SourceContractTests(unittest.TestCase):
    def test_missing_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            result = module.audit(Path(d))
            self.assertFalse(all(result.values()))
            self.assertEqual(len(result), len(module.FILES))

    def test_markers_all_present(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name, markers in module.FILES.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("\n".join(markers), encoding="utf-8")
            self.assertTrue(all(module.audit(root).values()))
            first = next(iter(module.FILES))
            (root / first).write_text("", encoding="utf-8")
            self.assertFalse(module.audit(root)[first])

if __name__ == "__main__":
    unittest.main()
