import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/"read-only-jni-mapping.py"
s=importlib.util.spec_from_file_location("jni_mapping",PATH)
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)

def st(pid=671,uid=1002):
    return "Pid:\t%d\nUid:\t%d\nTracerPid:\t0\n"%(pid,uid)

LINE="1234-5678 r-xp 00000000 00:00 0 /system/lib/libbluetooth_jni.so\n"

class Tests(unittest.TestCase):
    def test_exact_jni_mapping(self):
        r=m.summarize(LINE)
        self.assertEqual(r["jni_mapping_partition_categories"],["SYSTEM"])
        self.assertTrue(r["jni_library_mapped"])
        self.assertNotIn("/system/lib",json.dumps(r))

    def test_not_substring(self):
        r=m.summarize(LINE.replace("libbluetooth_jni.so","libbluetooth_jni.so.bak"))
        self.assertFalse(r["jni_library_mapped"])

    def test_missing_mapping_does_not_authorize(self):
        output=["671",st(),"droid.bluetooth\n","",st(),"671"]
        with patch.object(m,"read",side_effect=output):
            r=m.collect("serial")
        self.assertFalse(r["jni_library_mapped"])
        self.assertEqual(r["caller_linker_namespace"],"UNVERIFIED")
        self.assertEqual(r["decision"],"NO_GO")

    def test_changed_pid_rejected(self):
        output=["671",st(),"droid.bluetooth\n",LINE,st(),"672"]
        with patch.object(m,"read",side_effect=output):
            with self.assertRaises(ValueError):
                m.collect("serial")

    def test_mapping_sanitized(self):
        output=["671",st(),"droid.bluetooth\n",LINE,st(),"671"]
        with patch.object(m,"read",side_effect=output):
            r=m.collect("serial")
        self.assertEqual(r["jni_mapping_partition_categories"],["SYSTEM"])
        self.assertFalse(r["injection_authorized"])
        self.assertNotIn("671",json.dumps(r))
        self.assertNotIn("1234",json.dumps(r))

if __name__=="__main__":
    unittest.main()
