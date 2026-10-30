import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/"verify_hci_auth.py"
spec=importlib.util.spec_from_file_location("verify_hci_auth",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class TestHCIAuth(unittest.TestCase):
    def test_strict_sha(self):
        with self.assertRaisesRegex(ValueError,"SHA_MISMATCH"):
            m.audit(b"not-an-ELF")
    def test_opcode_and_callsite_pinned(self):
        self.assertEqual(m.INSTRUCTIONS[0x27c9ae],"40f21140")
        self.assertEqual(m.INSTRUCTIONS[0x2580c0],"24f06afc")
        self.assertEqual(m.INSTRUCTIONS[0x25b5e6],"8df8af10")
    def test_no_live_action_api(self):
        source=path.read_text()
        for unsafe in ("PTRACE_ATTACH","adb shell","su -c","systemctl restart","os.system("):
            self.assertNotIn(unsafe,source)
        self.assertIn("'injection_authorized':False",source)
if __name__=="__main__":unittest.main()
