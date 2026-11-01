import unittest
from cable_policy import Enrollment, Candidate, classify

E = Enrollment("usb-enrolled-controller-A", "builtin-m3-host", True, True)
R = Candidate("usb-enrolled-controller-A", "builtin-m3-host", 0x11,
              "HID_HOST", True, True)

class PolicyTests(unittest.TestCase):
    def test_matching_candidate_is_not_claimed_authenticated(self):
        self.assertEqual(classify(E, R), "CANDIDATE_ONLY_NOT_AUTHENTICATED")
    def test_missing_enrollment(self):
        self.assertEqual(classify(None, R), "DENY_NO_USB_ENROLLMENT")
    def test_missing_physical_usb_provenance(self):
        self.assertEqual(classify(Enrollment(E.controller_token,E.host_token,False,True),R), "DENY_NO_USB_ENROLLMENT")
    def test_unapproved_and_revoked(self):
        self.assertEqual(classify(Enrollment(E.controller_token,E.host_token,True,False),R), "DENY_NOT_AUTHORIZED")
        self.assertEqual(classify(Enrollment(E.controller_token,E.host_token,True,True,True),R), "DENY_NOT_AUTHORIZED")
    def test_wrong_controller(self):
        self.assertEqual(classify(E,Candidate("other",R.host_token,R.psm,R.profile,True,True)),"DENY_CONTROLLER_MISMATCH")
    def test_changed_host(self):
        self.assertEqual(classify(E,Candidate(R.controller_token,"other-host",R.psm,R.profile,True,True)),"DENY_HOST_MISMATCH")
    def test_psm_and_profile(self):
        self.assertEqual(classify(E,Candidate(R.controller_token,R.host_token,0x17,R.profile,True,True)),"DENY_NOT_DS3_HID_PATH")
        self.assertEqual(classify(E,Candidate(R.controller_token,R.host_token,0x13,"KEYBOARD",True,True)),"DENY_NOT_DS3_HID_PATH")
    def test_no_hooks(self):
        for n,h in ((False,True),(True,False),(False,False)):
            self.assertEqual(classify(E,Candidate(R.controller_token,R.host_token,0x13,"HID_HOST",n,h)), "DENY_MISSING_TWO_GATE_INTEGRATION")
    def test_duplicate(self):
        self.assertEqual(classify(E,Candidate(R.controller_token,R.host_token,0x11,"HID_HOST",True,True,True)), "DENY_DUPLICATE")

if __name__ == "__main__":
    unittest.main()
