import importlib.util
import io
import json
import pathlib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "read-only-health.py"
spec = importlib.util.spec_from_file_location("readonly_health", SOURCE)
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)

STATUS = "Uid:\t1002\t1002\t1002\t1002\nThreads:\t49\nTracerPid:\t0\n"
MAPS = ("0000-1000 r-xp 00000000 00:00 0 /system/lib/libbluetooth.so\n"
        "1000-2000 r-xp 00000000 00:00 0 /apex/com.android.runtime/bin/linker\n"
        "2000-3000 r-xp 00000000 00:00 0 /apex/com.android.runtime/lib/bionic/libdl.so\n")


class HealthTests(unittest.TestCase):
    def fixture(self, pid1="671", pid2="671", status=STATUS, maps=MAPS):
        return [pid1, "droid.bluetooth\n", status, maps, pid2]

    def test_good_snapshot_is_sanitized_and_no_go(self):
        with patch.object(health, "read", side_effect=self.fixture()) as mock:
            result = health.collect("test-device")
        self.assertTrue(result["identity_verified"])
        self.assertEqual(result["threads"], 49)
        self.assertFalse(result["injection_authorized"])
        self.assertEqual(result["linker_namespace_acceptance"], "UNVERIFIED")
        self.assertNotIn("671", json.dumps(result))
        self.assertNotIn("/system", json.dumps(result))
        commands = [call.args[1] for call in mock.call_args_list]
        self.assertEqual(len(commands), 5)
        self.assertTrue(all(x.startswith(("pidof ", "cat /proc/")) for x in commands))

    def test_pid_race_fails_closed(self):
        with patch.object(health, "read", side_effect=self.fixture(pid2="672")):
            with self.assertRaisesRegex(ValueError, "identity changed"):
                health.collect("test-device")

    def test_ambiguous_pid_is_rejected(self):
        self.assertRaises(ValueError, health.single_pid, "671 672")
        self.assertRaises(ValueError, health.single_pid, "1;reboot")
        self.assertRaises(ValueError, health.single_pid, "")

    def test_identity_and_tracer_fail_closed(self):
        for status in (STATUS.replace("1002", "0"), STATUS.replace("TracerPid:\t0", "TracerPid:\t12")):
            with self.subTest(status=status):
                with patch.object(health, "read", side_effect=self.fixture(status=status)):
                    with self.assertRaises(ValueError):
                        health.collect("serial")

    def test_missing_mapping_fails_closed(self):
        with patch.object(health, "read", side_effect=self.fixture(maps="")):
            with self.assertRaisesRegex(ValueError, "mapping missing"):
                health.collect("serial")

    def test_read_failure_no_sensitive_diagnostics(self):
        with patch.object(health, "read", side_effect=RuntimeError("read-only device command failed")):
            output = io.StringIO()
            with redirect_stderr(output):
                code = health.main(["device"])
            self.assertEqual(code, 2)
            self.assertNotIn("192.168", output.getvalue())
            self.assertFalse(json.loads(output.getvalue())["injection_authorized"])


if __name__ == "__main__":
    unittest.main()
