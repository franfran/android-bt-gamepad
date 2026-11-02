import unittest
from mock_l2cap_btm import MockBridge,Result

class CallbackTests(unittest.TestCase):
    def test_pending_async_success(self):
        b=MockBridge();b.new_link();t=b.incoming(7,Result.CMD_STARTED)
        self.assertEqual(b.events[-1][0],"PENDING")
        self.assertTrue(b.completion(t,Result.SUCCESS))
        self.assertEqual(b.events[-1][0],"SEC_COMP")

    def test_pending_async_failure(self):
        b=MockBridge();b.new_link();t=b.incoming(7,Result.CMD_STARTED)
        self.assertFalse(b.completion(t,Result.FAILURE))
        self.assertEqual(b.events[-1][0],"SEC_COMP_NEG")

    def test_synchronous_success_callback(self):
        b=MockBridge();b.new_link();t=b.incoming(8,Result.SUCCESS,callback_inline=True)
        self.assertEqual(b.events[-1],("SEC_COMP",t))

    def test_no_security_normalizes_only_in_existing_mock(self):
        b=MockBridge();b.new_link();t=b.incoming(8,Result.SUCCESS_NO_SECURITY,callback_inline=True)
        self.assertEqual(b.events[-1],("SEC_COMP",t))

    def test_no_callback_does_not_mean_success(self):
        b=MockBridge();b.new_link();t=b.incoming(8,Result.SUCCESS)
        self.assertEqual(b.events[-1],("WAIT_CALLBACK",t))

    def test_delay_check_not_admission(self):
        b=MockBridge();b.new_link();t=b.incoming(8,Result.CMD_STARTED)
        self.assertFalse(b.completion(t,Result.DELAY_CHECK))
        self.assertEqual(b.events[-1][0],"DELAY")

    def test_old_callback_after_disconnect_reconnect_rejected(self):
        b=MockBridge();b.new_link();old=b.incoming(8,Result.CMD_STARTED)
        b.disconnect();b.new_link();fresh=b.incoming(8,Result.CMD_STARTED)
        self.assertFalse(b.completion(old,Result.SUCCESS))
        self.assertTrue(b.completion(fresh,Result.SUCCESS))

    def test_duplicate_callback_rejected(self):
        b=MockBridge();b.new_link();t=b.incoming(8,Result.CMD_STARTED)
        self.assertTrue(b.completion(t,Result.SUCCESS))
        self.assertFalse(b.completion(t,Result.SUCCESS))

    def test_wrong_ccb_rejected(self):
        b=MockBridge();b.new_link();t=b.incoming(8,Result.CMD_STARTED)
        from mock_l2cap_btm import Ticket
        self.assertFalse(b.completion(Ticket(t.epoch,9),Result.SUCCESS))

    def test_started_is_not_valid_completion(self):
        b=MockBridge();b.new_link();t=b.incoming(8,Result.CMD_STARTED)
        self.assertFalse(b.completion(t,Result.CMD_STARTED))
if __name__=="__main__":
    unittest.main()
