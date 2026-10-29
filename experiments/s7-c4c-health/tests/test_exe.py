import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

path=Path(__file__).resolve().parents[1]/"read-only-exe.py"
spec=importlib.util.spec_from_file_location("exe_provenance",path)
tool=importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

def status(pid,ppid,uid=1002):
    return "Pid:\t%d\nPPid:\t%d\nUid:\t%d\nTracerPid:\t0\nThreads:\t48\n"%(pid,ppid,uid)

class ExecutableTests(unittest.TestCase):
    def test_executable_categories(self):
        self.assertEqual(tool.exe_class("/system/bin/app_process32"),"APP_PROCESS_BINARY")
        self.assertEqual(tool.exe_class("/system/bin/app_process32 (deleted)"),"APP_PROCESS_BINARY")
        self.assertEqual(tool.exe_class("/vendor/bin/bluetooth-service"),"PARTITION_NATIVE_BINARY")
        self.assertEqual(tool.exe_class("/data/local/tmp/secret"),"UNKNOWN")

    def test_zygote_binary_not_assumed_launch_proof(self):
        outputs=["671",status(671,133),"droid.bluetooth",status(133,1,0),
                 "/system/bin/app_process32","/system/bin/app_process32",
                 status(671,133),"671"]
        with patch.object(tool,"read",side_effect=outputs) as mock:
            result=tool.gather("serial")
        self.assertEqual(result["bluetooth_executable_category"],"APP_PROCESS_BINARY")
        self.assertEqual(result["launch_mechanism"],"UNVERIFIED")
        self.assertEqual(result["caller_linker_namespace"],"UNVERIFIED")
        self.assertFalse(result["injection_authorized"])
        self.assertNotIn("671",json.dumps(result))
        self.assertEqual(mock.call_count,8)

    def test_native_binary_not_namespace_acceptance(self):
        outputs=["671",status(671,1),"droid.bluetooth",status(1,0,0),
                 "/vendor/bin/android.hardware.bluetooth-service","/system/bin/init",
                 status(671,1),"671"]
        with patch.object(tool,"read",side_effect=outputs):
            result=tool.gather("serial")
        self.assertEqual(result["bluetooth_executable_category"],"PARTITION_NATIVE_BINARY")
        self.assertEqual(result["addon_path_permitted"],"UNVERIFIED")

    def test_pid_change_fails_closed(self):
        outputs=["671",status(671,133),"droid.bluetooth",status(133,1,0),
                 "/system/bin/app_process32","/system/bin/app_process32",
                 status(671,133),"672"]
        with patch.object(tool,"read",side_effect=outputs):
            with self.assertRaisesRegex(ValueError,"PID changed"):
                tool.gather("serial")

    def test_privacy_no_raw_executable(self):
        for raw in ("/private/key", "/system/bin/app_process32 (deleted)"):
            self.assertNotIn(raw, json.dumps({"class":tool.exe_class(raw)}))

if __name__=="__main__":
    unittest.main()
