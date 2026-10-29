import importlib.util
import json
import pathlib
import unittest
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "read-only-linkerconfig.py"
spec = importlib.util.spec_from_file_location("linkerconfig", SCRIPT)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

SAMPLE = """
dir.system=/system/bin
[system]
namespace.default.isolated=true
namespace.default.search.paths=/system/lib
namespace.default.permitted.paths=/system/lib
namespace.default.links=runtime
"""


class Tests(unittest.TestCase):
    def test_sanitized_static_summary(self):
        report = tool.summarize(SAMPLE)
        self.assertTrue(report["has_sections"])
        self.assertTrue(report["has_namespace_policy_keys"])
        self.assertNotIn("/system/lib", json.dumps(report))
        self.assertNotIn("default", json.dumps(report))

    def test_no_file_still_no_go(self):
        with patch.object(tool, "read_static", return_value=None):
            result = tool.inspect("serial")
        self.assertEqual(result["candidate_files_read"], 0)
        self.assertFalse(result["policy_inputs_observed"])
        self.assertEqual(result["linker_namespace_acceptance"], "UNVERIFIED")
        self.assertEqual(result["decision"], "NO_GO")

    def test_static_file_does_not_promote_acceptance(self):
        with patch.object(tool, "read_static", return_value=SAMPLE):
            result = tool.inspect("serial")
        self.assertTrue(result["any_namespace_keys_found"])
        self.assertEqual(result["addon_path_permitted"], "UNVERIFIED")
        self.assertFalse(result["injection_authorized"])

    def test_reject_unlisted_remote_paths(self):
        with self.assertRaises(ValueError):
            tool.read_static("serial", "/data/local/tmp/arbitrary")

    def test_adb_command_is_fixed_and_read_only(self):
        import subprocess
        value = subprocess.CompletedProcess([], 0, stdout=SAMPLE.encode(), stderr=b"")
        with patch.object(tool.subprocess, "run", return_value=value) as run:
            tool.read_static("serial", tool.CANDIDATES[0])
        args = run.call_args.args[0]
        self.assertEqual(args[:7], ["adb", "-s", "serial", "exec-out", "su", "0", "sh"])
        self.assertEqual(args[8], "cat " + tool.CANDIDATES[0])


if __name__ == "__main__":
    unittest.main()
