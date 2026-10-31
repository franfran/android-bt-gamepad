import unittest
from readiness_model import Readiness, CONTROL, INTERRUPT

class TestReadiness(unittest.TestCase):
    def test_candidates_alone_not_operational(self):
        s=Readiness();self.assertTrue(s.candidate(CONTROL));self.assertTrue(s.candidate(INTERRUPT))
        self.assertFalse(s.operational());self.assertFalse(s.native_connection())
    def test_interrupt_first_rejected(self):
        s=Readiness();self.assertFalse(s.candidate(INTERRUPT));self.assertTrue(s.candidate(CONTROL))
    def test_partial_config_no_native_connected(self):
        s=Readiness();s.candidate(CONTROL);s.candidate(INTERRUPT);s.configured(CONTROL)
        self.assertFalse(s.native_connection())
    def test_full_state_progression(self):
        s=Readiness();s.candidate(CONTROL);s.candidate(INTERRUPT)
        self.assertTrue(s.configured(CONTROL));self.assertTrue(s.configured(INTERRUPT))
        self.assertTrue(s.native_connection());self.assertFalse(s.operational())
        self.assertTrue(s.java_admission());self.assertFalse(s.operational())
        self.assertTrue(s.input_ready());self.assertFalse(s.operational())
        self.assertFalse(s.wireless_report_observed(valid=False,via_builtin_bt=True))
        self.assertTrue(s.wireless_report_observed(valid=True,via_builtin_bt=True));self.assertTrue(s.operational())
    def test_early_java_or_input_rejected(self):
        s=Readiness();self.assertFalse(s.java_admission());self.assertFalse(s.input_ready())
    def test_duplicate_psm_candidate_rejected(self):
        s=Readiness();self.assertTrue(s.candidate(CONTROL));self.assertFalse(s.candidate(CONTROL))
    def test_disconnect_clears(self):
        s=Readiness();s.candidate(CONTROL);s.candidate(INTERRUPT);s.configured(CONTROL);s.configured(INTERRUPT)
        s.native_connection();s.java_admission();s.input_ready();s.wireless_report_observed(valid=True,via_builtin_bt=True);s.disconnect()
        self.assertFalse(s.operational());self.assertFalse(s.candidate(CONTROL));self.assertEqual(s.candidate_psms,set())
    def test_reset_can_start_new_session(self):
        s=Readiness();s.candidate(CONTROL);s.disconnect();s.reset()
        self.assertTrue(s.candidate(CONTROL));self.assertFalse(s.operational())
    def test_usb_report_does_not_satisfy_wireless_requirement(self):
        s=Readiness();s.candidate(CONTROL);s.candidate(INTERRUPT)
        s.configured(CONTROL);s.configured(INTERRUPT)
        s.native_connection();s.java_admission();s.input_ready()
        self.assertFalse(s.wireless_report_observed(valid=True,via_builtin_bt=False))
        self.assertFalse(s.operational())
    def test_report_before_input_device_rejected(self):
        s=Readiness();self.assertFalse(s.wireless_report_observed(valid=True,via_builtin_bt=True))
        self.assertFalse(s.operational())
    def test_configure_unknown_channel_rejected(self):
        s=Readiness();self.assertFalse(s.configured(INTERRUPT))
if __name__=="__main__":unittest.main()
