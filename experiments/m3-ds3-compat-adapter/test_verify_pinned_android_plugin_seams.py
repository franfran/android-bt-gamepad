"""Host-only, synthetic unit checks: public pinned source extension gates."""
import contextlib
import io
import unittest
from unittest.mock import patch
import verify_pinned_android_plugin_seams as source


class PluginSourceGateTests(unittest.TestCase):
    def fixtures(self):
        texts = {
            path: "\n".join(fragment
                            for name, (filepath, evidence) in source.CHECKS.items()
                            if filepath == path
                            for fragment in evidence)
            for path in source.FILES
        }
        manifest = "packages/apps/Bluetooth/AndroidManifest.xml"
        texts[manifest] += "\n" + "\n".join(
            '<service android:name=".' + name + '"></service>'
            for name in source.M3_OBSERVED_BT_RESOLVER_SERVICES
        )
        return texts

    def test_ten_independent_source_predicates(self):
        check = source.check_texts(self.fixtures())
        self.assertEqual(len(source.CHECKS), len(check))
        self.assertEqual(len(check), len(set(check)))

    def test_fail_closed_missing_critical_native_callback(self):
        t = self.fixtures()
        p = "system/bt/btif/src/btif_hh.cc"
        t[p] = t[p].replace("bt_hh_callbacks = callbacks", "")
        with self.assertRaisesRegex(ValueError, "native_hidhost_callback_single_pointer"):
            source.check_texts(t)

    def test_fail_closed_missing_hid_privilege(self):
        t = self.fixtures()
        p = "packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java"
        t[p] = t[p].replace("enforceBluetoothPrivilegedPermission(service)", "")
        with self.assertRaisesRegex(ValueError, "android_hid_binder_privileged_connect"):
            source.check_texts(t)

    def test_fail_closed_missing_pairing_broadcast(self):
        t = self.fixtures()
        p = "packages/apps/Bluetooth/src/com/android/bluetooth/btservice/BondStateMachine.java"
        t[p] = t[p].replace("new Intent(BluetoothDevice.ACTION_PAIRING_REQUEST)", "")
        with self.assertRaisesRegex(ValueError, "pairing_broadcast_internal_source"):
            source.check_texts(t)

    def test_fail_closed_missing_bond_state_guard(self):
        t = self.fixtures()
        p = "packages/apps/Bluetooth/src/com/android/bluetooth/btservice/AdapterService.java"
        t[p] = t[p].replace("!deviceProp.isBondingOrBonded()", "")
        with self.assertRaisesRegex(ValueError, "app_pin_binder_state_and_permission"):
            source.check_texts(t)

    def test_actual_m3_service_resolver_coverage_all_22(self):
        manifest = self.fixtures()["packages/apps/Bluetooth/AndroidManifest.xml"]
        self.assertEqual(22, source.check_m3_resolver_public_manifest(manifest))

    def test_unexpected_oem_service_is_not_credited(self):
        manifest = self.fixtures()["packages/apps/Bluetooth/AndroidManifest.xml"]
        manifest = manifest.replace(
            '<service android:name=".hid.HidHostService"></service>', ""
        )
        with self.assertRaisesRegex(ValueError, "not covered"):
            source.check_m3_resolver_public_manifest(manifest)

    def test_receiver_component_does_not_count_as_service(self):
        manifest = self.fixtures()["packages/apps/Bluetooth/AndroidManifest.xml"]
        manifest = manifest.replace(
            '<service android:name=".hid.HidHostService"></service>',
            '<receiver android:name=".hid.HidHostService"></receiver>'
        )
        with self.assertRaisesRegex(ValueError, "not covered"):
            source.check_m3_resolver_public_manifest(manifest)

    def test_git_blob_sha_algorithm(self):
        # Git SHA-1 of empty Git blob: Git's canonical historical fixed value.
        self.assertEqual("e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
                         source.git_blob_sha(b""))

    def test_main_reports_only_bounded_public_source_result(self):
        with patch.object(source, "fetch_pinned", return_value=self.fixtures()):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = source.main()
        self.assertEqual(0, code)
        self.assertIn("PUBLIC_SOURCE_SEAMS_VERIFIED_NOT_OEM_PLUGIN_GO", output.getvalue())

    def test_main_refuses_fetch_failure_without_path_leak(self):
        with patch.object(source, "fetch_pinned", side_effect=ValueError("private path")):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = source.main()
        self.assertEqual(2, code)
        self.assertNotIn("private path", output.getvalue())


if __name__ == "__main__":
    unittest.main()
