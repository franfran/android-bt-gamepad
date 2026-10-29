import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

FILE = Path(__file__).resolve().parents[1] / "read-only-package-process.py"
spec = importlib.util.spec_from_file_location("pkgproc", FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def status(uid=1002):
    return ("Pid:\t671\nPPid:\t133\nUid:\t%d\t%d\t%d\t%d\nTracerPid:\t0\n" % (uid,uid,uid,uid)).encode()

class Tests(unittest.TestCase):
    def sample(self, cmd=b"com.android.bluetooth\x00", uid=b"package:com.android.bluetooth uid:1002\n"):
        return [b"671",status(),b"droid.bluetooth\n",cmd,uid,status(),b"671"]

    def test_matching_uid_and_cmdline_are_corroboration_only(self):
        with patch.object(mod, "read", side_effect=self.sample()) as mock:
            report=mod.collect("serial")
        self.assertEqual(report["package_process_association"],"CORROBORATED")
        self.assertEqual(report["caller_linker_namespace"],"UNVERIFIED")
        self.assertEqual(report["apk_classloader_link"],"UNVERIFIED")
        self.assertEqual(report["decision"],"NO_GO")
        self.assertNotIn("671",json.dumps(report))
        self.assertEqual(mock.call_count,7)

    def test_other_cmdline_not_proof(self):
        with patch.object(mod,"read",side_effect=self.sample(cmd=b"com.oem.bluetooth\x00")):
            report=mod.collect("serial")
        self.assertEqual(report["package_process_association"],"UNVERIFIED")

    def test_shared_uid_not_sufficient(self):
        with patch.object(mod,"read",side_effect=self.sample(cmd=b"unrelated\x00")):
            report=mod.collect("serial")
        self.assertTrue(report["package_uid_matches_process"])
        self.assertEqual(report["package_process_association"],"UNVERIFIED")

    def test_mismatched_uid_not_corroborated(self):
        with patch.object(mod,"read",side_effect=self.sample(uid=b"package:com.android.bluetooth uid:1003\n")):
            report=mod.collect("serial")
        self.assertFalse(report["package_uid_matches_process"])
        self.assertEqual(report["package_process_association"],"UNVERIFIED")

    def test_ambiguous_package_metadata_fails(self):
        with self.assertRaises(ValueError):
            mod.package_uid(b"package:com.android.bluetooth uid:1002\npackage:com.oem uid:1002")

    def test_changed_pid_rejected(self):
        x=self.sample()
        x[-1]=b"672"
        with patch.object(mod,"read",side_effect=x):
            with self.assertRaisesRegex(RuntimeError,"stage_revalidation"):
                mod.collect("serial")

    def test_package_uid_stage_redacted(self):
        output=[b"671", status(), b"droid.bluetooth\\n", b"com.android.bluetooth\\x00"] + [b"unexpected private OEM format"] * 3
        with patch.object(mod,"read",side_effect=output):
            with self.assertRaisesRegex(RuntimeError,"stage_package_uid"):
                mod.collect("serial")

    def test_generic_error_stage_does_not_include_raw_data(self):
        import io
        from contextlib import redirect_stderr
        output=[b"671", status(), b"droid.bluetooth\\n", b"com.android.bluetooth\\x00"] + [b"secret OEM data"] * 3
        with patch.object(mod,"read",side_effect=output):
            error=io.StringIO()
            with redirect_stderr(error):
                code=mod.main(["serial"])
        self.assertEqual(code,2)
        data=json.loads(error.getvalue())
        self.assertEqual(data["failure_stage"],"stage_package_uid")
        self.assertNotIn("secret OEM",error.getvalue())

    def test_package_uid_second_command_fallback(self):
        responses = [b"671", status(), b"droid.bluetooth\\n", b"com.android.bluetooth\\x00",
                     b"OEM unknown output", b"package:com.android.bluetooth uid:1002\\n",
                     status(), b"671"]
        with patch.object(mod, "read", side_effect=responses):
            report=mod.collect("serial")
        self.assertEqual(report["package_process_association"], "CORROBORATED")

    def test_cmdline_sanitization(self):
        self.assertEqual(mod.cmdline_category(b"com.android.bluetooth\x00--secret"),
                         "EXACT_PACKAGE_PROCESS_NAME")
        self.assertEqual(mod.cmdline_category(b"--private-host-identifier"),
                         "OTHER_PROCESS_NAME")

if __name__=="__main__":
    unittest.main()
