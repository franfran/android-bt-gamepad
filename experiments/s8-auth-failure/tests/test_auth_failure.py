import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/"verify_auth_failure.py"
s=importlib.util.spec_from_file_location("auth_failure",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class TestAuthFailure(unittest.TestCase):
    def test_exact_known_sites(self):
        self.assertEqual(len(m.CHECKS),19)
        self.assertEqual(m.CHECKS[0x2580c0],"f024fc6a")
        self.assertEqual(m.CHECKS[0x25b844],"f88a5129")
        self.assertEqual(m.CHECKS[0x25b934],"47b8")
    def test_original_sha_is_required(self):
        with self.assertRaisesRegex(ValueError,"SHA_MISMATCH"):
            m.audit(b"not original")
    def test_no_live_device_actions(self):
        txt=p.read_text()
        for key in ("PTRACE_ATTACH","adb shell","su -c","systemctl restart"):
            self.assertNotIn(key,txt)
        self.assertIn('"injection_authorized":False',txt)
if __name__=="__main__":unittest.main()
