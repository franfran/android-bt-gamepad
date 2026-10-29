import importlib.util
import json
import pathlib
import unittest
from unittest.mock import patch

FILE=pathlib.Path(__file__).resolve().parents[1]/"read-only-launch.py"
spec=importlib.util.spec_from_file_location("launch",FILE)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def status(pid,ppid,uid=1002,tracer=0):
    return "Pid:\t%d\nPPid:\t%d\nUid:\t%d\t%d\t%d\t%d\nThreads:\t48\nTracerPid:\t%d\n"%(pid,ppid,uid,uid,uid,uid,tracer)

class LaunchTests(unittest.TestCase):
    def fixtures(self, parent="zygote",last="671"):
        return ["671","droid.bluetooth",status(671,133),status(133,1,0),
                parent,last,status(671,133)]

    def test_zygote_observation_never_promotes_namespace(self):
        with patch.object(mod,"adb_read",side_effect=self.fixtures()) as call:
            data=mod.collect("serial")
        self.assertEqual(data["parent_classification"],"ZYGOTE_PARENT_OBSERVED")
        self.assertEqual(data["caller_linker_namespace"],"UNVERIFIED")
        self.assertEqual(data["decision"],"NO_GO")
        self.assertNotIn("671",json.dumps(data))
        self.assertEqual(call.call_count,7)

    def test_nonzygote_parent_is_not_native_proof(self):
        with patch.object(mod,"adb_read",side_effect=self.fixtures(parent="init")):
            data=mod.collect("serial")
        self.assertEqual(data["parent_classification"],"NON_ZYGOTE_PARENT_OBSERVED")
        self.assertEqual(data["launch_namespace"],"UNVERIFIED")

    def test_pid_change_rejected(self):
        with patch.object(mod,"adb_read",side_effect=self.fixtures(last="672")):
            with self.assertRaisesRegex(ValueError,"changed"):
                mod.collect("serial")

    def test_ambiguous_pid_rejected(self):
        with self.assertRaises(ValueError):
            mod.pid("671 672")

    def test_traced_target_rejected(self):
        seq=self.fixtures()
        seq[2]=status(671,133,tracer=5)
        with patch.object(mod,"adb_read",side_effect=seq):
            with self.assertRaises(ValueError):
                mod.collect("serial")

    def test_unknown_parent_does_not_assume_native(self):
        self.assertEqual(mod.classify({}, "UNKNOWN"),"UNKNOWN")

if __name__=="__main__":
    unittest.main()
