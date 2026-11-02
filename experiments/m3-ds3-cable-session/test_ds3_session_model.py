"""Offline tests for a symbolic CableSession, not Bluetooth validation."""
import unittest
from ds3_session_model import CableSession, Phase

def enrolled():
    m = CableSession()
    assert m.enroll(physical_usb_confirmed=True, owner_approved=True)
    return m

def connected():
    m = enrolled()
    e = m.connect(trusted_peer_proven=True)  # hypothetical oracle only
    assert e is not None
    return m, e

class PolicyTests(unittest.TestCase):
    def test_usb_requires_approval(self):
        m = CableSession()
        self.assertFalse(m.enroll(physical_usb_confirmed=True, owner_approved=False))
        self.assertFalse(m.enroll(physical_usb_confirmed=False, owner_approved=True))
        self.assertIsNone(m.connect(trusted_peer_proven=True))

    def test_radio_identity_unproven_fails_closed(self):
        self.assertIsNone(enrolled().connect(trusted_peer_proven=False))

    def test_control_then_interrupt_then_java_then_uhid(self):
        m, e = connected()
        self.assertTrue(m.channel(e, psm=0x11))
        self.assertTrue(m.channel(e, psm=0x13))
        self.assertTrue(m.java_admit(e))
        self.assertFalse(m.uhid_ready(e, report_completion_verified=False))
        self.assertTrue(m.uhid_ready(e, report_completion_verified=True))
        self.assertEqual(m.phase, Phase.ACTIVE)

    def test_interrupt_before_control_rejected(self):
        m, e = connected()
        self.assertFalse(m.channel(e, psm=0x13))
        self.assertFalse(m.java_admit(e))

    def test_duplicate_control_and_unrelated_psm_rejected(self):
        m, e = connected()
        self.assertFalse(m.channel(e, psm=0x17))
        self.assertTrue(m.channel(e, psm=0x11))
        self.assertFalse(m.channel(e, psm=0x11))

    def test_java_quiet_forbidden_fail(self):
        for args in ({'quiet': True}, {'forbidden': True}):
            m, e = connected()
            m.channel(e, psm=0x11)
            m.channel(e, psm=0x13)
            self.assertFalse(m.java_admit(e, **args))

    def test_disconnect_stale_reconnect_even_with_same_peer(self):
        m, old = connected()
        m.disconnect()
        fresh = m.connect(trusted_peer_proven=True)
        self.assertIsNotNone(fresh)
        self.assertNotEqual(old.epoch, fresh.epoch)
        self.assertFalse(m.channel(old, psm=0x11))
        self.assertTrue(m.channel(fresh, psm=0x11))

    def test_revoke_invalidates_active_event(self):
        m, e = connected()
        m.revoke()
        self.assertFalse(m.channel(e, psm=0x11))
        self.assertIsNone(m.connect(trusted_peer_proven=True))

    def test_adapter_change_invalidates_enrollment(self):
        m, e = connected()
        m.adapter_changed()
        self.assertFalse(m.channel(e, psm=0x11))
        self.assertIsNone(m.connect(trusted_peer_proven=True))

    def test_stale_java_callback_denied(self):
        m, old = connected()
        m.channel(old, psm=0x11)
        m.channel(old, psm=0x13)
        m.disconnect()
        fresh = m.connect(trusted_peer_proven=True)
        m.channel(fresh, psm=0x11)
        m.channel(fresh, psm=0x13)
        self.assertFalse(m.java_admit(old))
        self.assertTrue(m.java_admit(fresh))

if __name__ == '__main__':
    unittest.main()
