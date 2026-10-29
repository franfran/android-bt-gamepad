import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/"read-only-apk-origin.py"
spec=importlib.util.spec_from_file_location("apk_origin",PATH)
tool=importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

class ApkOriginTests(unittest.TestCase):
    def test_system_apk_is_not_namespace_proof(self):
        result=tool.classify("package:/system/app/Bluetooth/Bluetooth.apk\n")
        self.assertEqual(result["apk_partition_categories"],["SYSTEM"])
        self.assertEqual(result["classloader_namespace"],"UNVERIFIED")
        self.assertEqual(result["addon_path_permitted"],"UNVERIFIED")
        self.assertFalse(result["injection_authorized"])
        self.assertNotIn("/system/app",json.dumps(result))

    def test_multiple_apks_are_sanitized(self):
        result=tool.classify("package:/system_ext/priv-app/BT/base.apk\npackage:/system_ext/priv-app/BT/split.apk\n")
        self.assertEqual(result["apk_paths_observed"],2)
        self.assertEqual(result["apk_partition_categories"],["SYSTEM_EXT"])

    def test_unknown_partition_never_promotes(self):
        result=tool.classify("package:/unknown/OEM.apk\n")
        self.assertEqual(result["apk_partition_categories"],["UNKNOWN"])
        self.assertEqual(result["decision"],"NO_GO")

    def test_invalid_output_fails_closed(self):
        for x in ("", "Error: not found", "package:/system/../data/evil.apk"):
            with self.subTest(x=x):
                with self.assertRaises(ValueError):
                    tool.classify(x)

    def test_adb_invocation_fixed_and_read_only(self):
        p=subprocess.CompletedProcess([],0,b"package:/system/app/BT/base.apk\n",b"")
        with patch.object(tool.subprocess,"run",return_value=p) as run:
            tool.collect("M3SERIAL")
        self.assertEqual(run.call_args.args[0],
                         ["adb","-s","M3SERIAL","exec-out","pm","path","com.android.bluetooth"])

if __name__=="__main__":
    unittest.main()
