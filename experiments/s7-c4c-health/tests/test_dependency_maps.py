import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

f=Path(__file__).resolve().parents[1]/"read-only-dependency-maps.py"
s=importlib.util.spec_from_file_location("depmaps",f)
m=importlib.util.module_from_spec(s)
s.loader.exec_module(m)

def status():
    return "Pid:\t671\nUid:\t1002\nTracerPid:\t0\n"

class Tests(unittest.TestCase):
    def test_full_basename_partition(self):
        maps=("123-456 r-xp 0 00:00 0 /system/lib/libbase.so\n"
              "123-456 r-xp 0 00:00 0 /apex/com.android.runtime/lib/bionic/libc.so\n"
              "123-456 r-xp 0 00:00 0 /data/libchrome.so.bak\n")
        records={r["library"]:r for r in m.summarize(maps)}
        self.assertEqual(records["libbase.so"]["partition_categories"],["SYSTEM"])
        self.assertEqual(records["libc.so"]["partition_categories"],["APEX"])
        self.assertFalse(records["libchrome.so"]["mapped"])

    def test_pid_race_fails_closed(self):
        values=["671",status(),"droid.bluetooth\n","",status(),"672"]
        with patch.object(m,"read",side_effect=values):
            with self.assertRaises(ValueError):
                m.collect("serial")

    def test_unchanged_unmapped_still_no_go(self):
        values=["671",status(),"droid.bluetooth\n","",status(),"671"]
        with patch.object(m,"read",side_effect=values):
            result=m.collect("serial")
        self.assertEqual(len(result["needed_library_map_evidence"]),8)
        self.assertEqual(result["runtime_dependency_resolution"],"UNVERIFIED")
        self.assertFalse(result["injection_authorized"])
        self.assertEqual(result["decision"],"NO_GO")

if __name__=="__main__":
    unittest.main()
