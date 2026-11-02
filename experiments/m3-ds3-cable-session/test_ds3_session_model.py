"""Offline unit tests; no Bluetooth radio authentication or device I/O."""
import unittest
from ds3_session_model import CableSession, Phase
CLAIM = "abstract-controller-A"

def enrolled(risk=True):
    m=CableSession()
    assert m.enroll(physical_usb_confirmed=True,owner_approved=True,controller_claim=CLAIM)
    m.authorize_risk(risk)
    return m

def connected():
    m=enrolled()
    e=m.connect(radio_claim=CLAIM)
    assert e is not None
    return m,e

def channels(m,e):
    assert m.channel(e,psm=0x11)
    assert m.channel(e,psm=0x13)

class PolicyTests(unittest.TestCase):
    def test_usb_requires_physical_and_owner_approval_and_claim(self):
        m=CableSession()
        self.assertFalse(m.enroll(physical_usb_confirmed=False,owner_approved=True,controller_claim=CLAIM))
        self.assertFalse(m.enroll(physical_usb_confirmed=True,owner_approved=False,controller_claim=CLAIM))
        self.assertFalse(m.enroll(physical_usb_confirmed=True,owner_approved=True,controller_claim=""))

    def test_bounded_risk_required(self):
        self.assertIsNone(enrolled(False).connect(radio_claim=CLAIM))

    def test_unknown_peer_fails_closed(self):
        self.assertIsNone(enrolled().connect(radio_claim="unknown"))

    def test_wrong_transport_rejected(self):
        self.assertIsNone(enrolled().connect(radio_claim=CLAIM,transport="LE"))

    def test_gamepad_path(self):
        m,e=connected();channels(m,e)
        self.assertTrue(m.allow_descriptor(e,validated_gamepad_only=True))
        self.assertTrue(m.java_admit(e))
        self.assertFalse(m.uhid_ready(e,report_completion_verified=False))
        self.assertTrue(m.uhid_ready(e,report_completion_verified=True))
        self.assertEqual(m.phase,Phase.ACTIVE)
        self.assertTrue(m.input_report(e,validated_report=True))

    def test_interrupt_first(self):
        m,e=connected()
        self.assertFalse(m.channel(e,psm=0x13))
        self.assertFalse(m.java_admit(e))

    def test_unrelated_or_duplicate_psm(self):
        m,e=connected()
        self.assertFalse(m.channel(e,psm=0x17))
        self.assertTrue(m.channel(e,psm=0x11))
        self.assertFalse(m.channel(e,psm=0x11))

    def test_descriptor_required_and_reject_keyboard(self):
        m,e=connected();channels(m,e)
        self.assertFalse(m.allow_descriptor(e,validated_gamepad_only=False))
        self.assertFalse(m.java_admit(e))

    def test_java_quiet_and_forbidden(self):
        for kwargs in ({"quiet":True},{"forbidden":True}):
            m,e=connected();channels(m,e)
            m.allow_descriptor(e,validated_gamepad_only=True)
            self.assertFalse(m.java_admit(e,**kwargs))

    def test_invalid_report_denied(self):
        m,e=connected();channels(m,e)
        m.allow_descriptor(e,validated_gamepad_only=True)
        m.java_admit(e);m.uhid_ready(e,report_completion_verified=True)
        self.assertFalse(m.input_report(e,validated_report=False))

    def test_reconnect_stale_java_event(self):
        m,old=connected();channels(m,old);m.allow_descriptor(old,validated_gamepad_only=True)
        m.disconnect()
        new=m.connect(radio_claim=CLAIM)
        self.assertNotEqual(old.epoch,new.epoch)
        channels(m,new);m.allow_descriptor(new,validated_gamepad_only=True)
        self.assertFalse(m.java_admit(old))
        self.assertTrue(m.java_admit(new))

    def test_revoke(self):
        m,e=connected();m.revoke()
        self.assertFalse(m.channel(e,psm=0x11))
        self.assertIsNone(m.connect(radio_claim=CLAIM))

    def test_adapter_change(self):
        m,e=connected();m.adapter_changed()
        self.assertFalse(m.channel(e,psm=0x11))

    def test_risk_revocation_invalidates_existing_event(self):
        m,e=connected();m.authorize_risk(False)
        self.assertFalse(m.channel(e,psm=0x11))
        self.assertIsNone(m.connect(radio_claim=CLAIM))

    def test_reenroll_invalidates_prior_epoch_and_risk(self):
        m,e=connected()
        self.assertTrue(m.enroll(physical_usb_confirmed=True,owner_approved=True,controller_claim=CLAIM))
        self.assertFalse(m.channel(e,psm=0x11))
        self.assertIsNone(m.connect(radio_claim=CLAIM))

    def test_disconnect_invalidates_input(self):
        m,e=connected();channels(m,e)
        m.allow_descriptor(e,validated_gamepad_only=True)
        m.java_admit(e);m.uhid_ready(e,report_completion_verified=True)
        m.disconnect()
        self.assertFalse(m.input_report(e,validated_report=True))

if __name__=="__main__":
    unittest.main()
