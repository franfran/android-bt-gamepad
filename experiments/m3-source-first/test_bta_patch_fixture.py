"""Offline fixture for experimental BTA guard patch; not proof of runtime safety."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATCH = ROOT / "experiments/m3-source-first/bta_w4_guard_EXPERIMENTAL.patch"
TARGET = pathlib.Path("system/bt/bta/hh/bta_hh_act.cc")
ANCHOR = '''    const uint8_t api_sndcmd_param =
        convert_api_sndcmd_param(p_data->api_sndcmd);

    if (HID_HostWriteDev(p_cb->hid_handle, p_data->api_sndcmd.t_type,
'''

class PatchFixture(unittest.TestCase):
    def test_applies_to_exact_context_and_rejects_divergence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            target = root / TARGET
            target.parent.mkdir(parents=True)
            target.write_text("\n" * 1027 + ANCHOR)
            good = subprocess.run(["git", "apply", "--check", str(PATCH)], cwd=root,
                                  capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            applied = subprocess.run(["git", "apply", str(PATCH)], cwd=root,
                                     capture_output=True, text=True)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            result = target.read_text()
            self.assertIn("expects_handshake && p_cb->w4_evt != 0", result)
            self.assertIn("osi_free(p_data->api_sndcmd.p_data)", result)
            self.assertNotEqual(subprocess.run(["git", "apply", "--check", str(PATCH)],
                                               cwd=root, capture_output=True).returncode, 0)

if __name__ == "__main__":
    unittest.main()
