import unittest
from dual_channel_policy import (Session, CONTROL, INTERRUPT,
                                 admit_candidate, complete, revoke)

def new_session():
    return Session("usb-controller-token", "m3-host-token", True, True, 100)

def attempt(s, psm=CONTROL, **changes):
    kw = dict(peer="usb-controller-token",host="m3-host-token",
              psm=psm,inbound=True,classic=True,now=5)
    kw.update(changes)
    return admit_candidate(s,**kw)

class DualChannelTests(unittest.TestCase):
    def test_normal_two_channels_both_accepted_as_candidates(self):
        s=new_session()
        self.assertEqual(attempt(s), "CANDIDATE_ONLY_NOT_AUTHENTICATED")
        self.assertFalse(complete(s))
        self.assertEqual(attempt(s,INTERRUPT),"CANDIDATE_ONLY_NOT_AUTHENTICATED")
        self.assertTrue(complete(s))
    def test_repeat_control_not_second_valid_channel(self):
        s=new_session(); attempt(s)
        self.assertEqual(attempt(s),"DENY_SAME_CHANNEL_DUPLICATE")
        self.assertEqual(s.channels,{CONTROL})
    def test_interrupt_first_fails_closed(self):
        s=new_session()
        self.assertEqual(attempt(s,INTERRUPT),"DENY_INTERRUPT_BEFORE_CONTROL")
        self.assertFalse(complete(s))
    def test_wrong_peer_or_host(self):
        for bad in (dict(peer="other"),dict(host="other")):
            s=new_session()
            self.assertEqual(attempt(s,**bad),"DENY_IDENTITY_MISMATCH")
            self.assertFalse(complete(s))
    def test_wrong_psm_classic_and_direction(self):
        for bad in (dict(psm=0x17),dict(classic=False),dict(inbound=False)):
            s=new_session()
            self.assertEqual(attempt(s,**bad),"DENY_WRONG_TRANSPORT_OR_PSM")
    def test_not_enrolled_or_approved(self):
        for changes in (dict(enrolled_by_usb=False),dict(owner_approved=False),dict(revoked=True)):
            s=new_session()
            for k,v in changes.items(): setattr(s,k,v)
            self.assertEqual(attempt(s),"DENY_NOT_AUTHORIZED")
    def test_expiry_clears_both_channels(self):
        s=new_session();attempt(s)
        self.assertEqual(attempt(s,INTERRUPT,now=100),"DENY_EXPIRED")
        self.assertFalse(complete(s)); self.assertFalse(s.channels)
    def test_revocation_clears_both_channels(self):
        s=new_session();attempt(s);revoke(s)
        self.assertEqual(attempt(s,INTERRUPT),"DENY_NOT_AUTHORIZED")
        self.assertFalse(complete(s));self.assertFalse(s.channels)
    def test_success_never_claimed_to_be_bonded_or_authenticated(self):
        s=new_session();attempt(s);attempt(s,INTERRUPT)
        self.assertEqual(s.channels,{CONTROL,INTERRUPT})
        self.assertFalse(hasattr(s,"bonded"))
        self.assertFalse(hasattr(s,"authenticated"))

if __name__=="__main__":unittest.main()
