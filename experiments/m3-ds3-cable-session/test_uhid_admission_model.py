"""Negative tests for STRICT proposed UHID pre-admission ordering."""
import unittest
from uhid_admission_model import AdmissionGate


class UhidAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.g = AdmissionGate()
        self.t = self.g.opened(7, native_ok=True)

    def test_native_denial_blocks_descriptor_and_create(self):
        t = self.g.opened(8, native_ok=False)
        self.assertFalse(self.g.descriptor_event(t, validated_gamepad=True))
        self.assertFalse(self.g.java_decision(t, permitted=True))
        self.assertFalse(self.g.uhid_create(t))

    def test_descriptor_first_does_not_create_before_java(self):
        self.assertTrue(self.g.descriptor_event(self.t, validated_gamepad=True))
        self.assertFalse(self.g.uhid_create(self.t))
        self.assertTrue(self.g.java_decision(self.t, permitted=True))
        self.assertTrue(self.g.uhid_create(self.t))

    def test_java_first_does_not_create_before_descriptor(self):
        self.assertTrue(self.g.java_decision(self.t, permitted=True))
        self.assertFalse(self.g.uhid_create(self.t))
        self.assertTrue(self.g.descriptor_event(self.t, validated_gamepad=True))
        self.assertTrue(self.g.uhid_create(self.t))

    def test_bad_descriptor_denied(self):
        self.g.java_decision(self.t, permitted=True)
        self.assertFalse(self.g.descriptor_event(self.t, validated_gamepad=False))
        self.assertFalse(self.g.uhid_create(self.t))

    def test_java_rejection_invalidates_native_candidate(self):
        self.g.descriptor_event(self.t, validated_gamepad=True)
        self.assertFalse(self.g.java_decision(self.t, permitted=False))
        self.assertFalse(self.g.uhid_create(self.t))

    def test_ready_for_data_not_authorization(self):
        self.assertFalse(self.g.kernel_ready(self.t, True))
        self.assertFalse(self.g.uhid_input(self.t, validated_report=True))

    def test_report_needs_native_java_create_kernel_and_validation(self):
        self.g.descriptor_event(self.t, validated_gamepad=True)
        self.g.java_decision(self.t, permitted=True)
        self.g.uhid_create(self.t)
        self.assertFalse(self.g.uhid_input(self.t, validated_report=True))
        self.assertTrue(self.g.kernel_ready(self.t, True))
        self.assertFalse(self.g.uhid_input(self.t, validated_report=False))
        self.assertTrue(self.g.uhid_input(self.t, validated_report=True))

    def test_stale_descriptor_event_cannot_attach_to_reused_handle(self):
        old = self.t
        self.g.close(old)
        new = self.g.opened(7, native_ok=True)
        self.assertFalse(self.g.descriptor_event(old, validated_gamepad=True))
        self.assertFalse(self.g.uhid_create(new))

    def test_stale_java_rejection_cannot_revoke_new_session(self):
        old = self.t
        new = self.g.opened(7, native_ok=True)
        self.assertFalse(self.g.java_decision(old, permitted=False))
        self.assertTrue(self.g.java_decision(new, permitted=True))

    def test_parallel_handles_keep_distinct_descriptor_decisions(self):
        other = self.g.opened(8, native_ok=True)
        self.g.java_decision(self.t, permitted=True)
        self.g.java_decision(other, permitted=True)
        self.assertTrue(self.g.descriptor_event(other, validated_gamepad=True))
        self.assertFalse(self.g.uhid_create(self.t))
        self.assertTrue(self.g.uhid_create(other))

    def test_close_revokes_prior_input(self):
        self.g.descriptor_event(self.t, validated_gamepad=True)
        self.g.java_decision(self.t, permitted=True)
        self.g.uhid_create(self.t)
        self.g.kernel_ready(self.t, True)
        self.assertTrue(self.g.uhid_input(self.t, validated_report=True))
        self.g.close(self.t)
        self.assertFalse(self.g.uhid_input(self.t, validated_report=True))


if __name__ == '__main__':
    unittest.main()
