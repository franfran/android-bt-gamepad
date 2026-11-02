"""Host-only fail-closed tests for proposed descriptor callback correlation."""
import unittest
from descriptor_envelope_model import DescriptorEnvelopeGate, Ticket


class DescriptorEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.g = DescriptorEnvelopeGate()
        self.a = self.g.opened(4, native_allowed=True)

    def test_java_before_descriptor_waits(self):
        self.assertTrue(self.g.java_decision(self.a, allowed=True))
        self.assertIsNone(self.g.release_uhid_create(self.a))
        self.assertTrue(self.g.accept_descriptor(self.a, b'gamepad', descriptor_valid=True))
        self.assertEqual(self.g.release_uhid_create(self.a), b'gamepad')

    def test_descriptor_before_java_waits(self):
        self.assertTrue(self.g.accept_descriptor(self.a, b'gamepad', descriptor_valid=True))
        self.assertIsNone(self.g.release_uhid_create(self.a))
        self.assertTrue(self.g.java_decision(self.a, allowed=True))
        self.assertEqual(self.g.release_uhid_create(self.a), b'gamepad')

    def test_interleaved_devices_not_swapped(self):
        b = self.g.opened(5, native_allowed=True)
        self.assertEqual(self.g.legacy_unbound_target(), 5)
        self.assertTrue(self.g.accept_descriptor(self.a, b'A', descriptor_valid=True))
        self.assertTrue(self.g.accept_descriptor(b, b'B', descriptor_valid=True))
        self.g.java_decision(self.a, allowed=True)
        self.g.java_decision(b, allowed=True)
        self.assertEqual(self.g.release_uhid_create(self.a), b'A')
        self.assertEqual(self.g.release_uhid_create(b), b'B')

    def test_reused_handle_old_epoch_dropped(self):
        new = self.g.opened(4, native_allowed=True)
        self.assertFalse(self.g.accept_descriptor(self.a, b'old', descriptor_valid=True))
        self.assertFalse(self.g.java_decision(self.a, allowed=False))
        self.assertTrue(self.g.accept_descriptor(new, b'new', descriptor_valid=True))

    def test_wrong_epoch_dropped(self):
        self.assertFalse(self.g.accept_descriptor(Ticket(4, self.a.epoch + 100), b'bad', descriptor_valid=True))

    def test_native_unapproved_rejected(self):
        untrusted = self.g.opened(5, native_allowed=False)
        self.assertFalse(self.g.accept_descriptor(untrusted, b'A', descriptor_valid=True))
        self.assertFalse(self.g.java_decision(untrusted, allowed=True))

    def test_descriptor_validation_required(self):
        self.assertFalse(self.g.accept_descriptor(self.a, b'keyboard', descriptor_valid=False))
        self.g.java_decision(self.a, allowed=True)
        self.assertIsNone(self.g.release_uhid_create(self.a))

    def test_descriptor_is_deep_copied(self):
        mutable = bytearray(b'gamepad')
        self.g.accept_descriptor(self.a, mutable, descriptor_valid=True)
        mutable[:] = b'changed'
        self.g.java_decision(self.a, allowed=True)
        self.assertEqual(self.g.release_uhid_create(self.a), b'gamepad')

    def test_java_denied_erases_descriptor(self):
        self.g.accept_descriptor(self.a, b'gamepad', descriptor_valid=True)
        self.assertFalse(self.g.java_decision(self.a, allowed=False))
        self.assertIsNone(self.g.release_uhid_create(self.a))

    def test_duplicate_descriptor_or_release_denied(self):
        self.g.accept_descriptor(self.a, b'good', descriptor_valid=True)
        self.assertFalse(self.g.accept_descriptor(self.a, b'bad', descriptor_valid=True))
        self.g.java_decision(self.a, allowed=True)
        self.assertEqual(self.g.release_uhid_create(self.a), b'good')
        self.assertIsNone(self.g.release_uhid_create(self.a))

    def test_disconnect_one_keeps_other(self):
        b = self.g.opened(5, native_allowed=True)
        self.g.accept_descriptor(b, b'B', descriptor_valid=True)
        self.g.java_decision(b, allowed=True)
        self.assertTrue(self.g.disconnect(self.a))
        self.assertFalse(self.g.accept_descriptor(self.a, b'A', descriptor_valid=True))
        self.assertEqual(self.g.release_uhid_create(b), b'B')

    def test_empty_descriptor_denied(self):
        self.assertFalse(self.g.accept_descriptor(self.a, b'', descriptor_valid=True))


if __name__ == '__main__':
    unittest.main()
