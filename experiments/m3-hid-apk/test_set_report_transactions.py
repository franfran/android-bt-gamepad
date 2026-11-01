import unittest
from set_report_transactions import SetReportTransactions

class TestSetReportTransactions(unittest.TestCase):
    def test_completion_preserves_id_and_raw_status(self):
        t = SetReportTransactions()
        self.assertTrue(t.submit("ds3", 234, now=0, timeout=5))
        c = t.complete("ds3", native_status=7, now=2)
        self.assertEqual((c.request_id, c.native_status), (234, 7))

    def test_no_fabricated_or_parallel_response(self):
        t = SetReportTransactions()
        self.assertIsNone(t.complete("a", native_status=0, now=0))
        self.assertTrue(t.submit("a", 1, now=0, timeout=5))
        self.assertFalse(t.submit("a", 2, now=1, timeout=5))

    def test_timeout_quarantines_late_callback(self):
        t = SetReportTransactions()
        t.submit("a", 1, now=0, timeout=5)
        self.assertTrue(t.expire("a", now=5))
        self.assertIsNone(t.complete("a", native_status=0, now=6))
        self.assertFalse(t.submit("a", 2, now=7, timeout=5))

    def test_completion_after_deadline_also_poisoned(self):
        t = SetReportTransactions()
        t.submit("a", 1, now=0, timeout=5)
        self.assertIsNone(t.complete("a", native_status=0, now=5))
        self.assertTrue(t.quarantined("a"))

    def test_disconnect_quarantines_pending(self):
        t = SetReportTransactions()
        t.submit("a", 1, now=0, timeout=5)
        t.disconnect("a")
        self.assertIsNone(t.complete("a", native_status=0, now=1))
        self.assertFalse(t.submit("a", 2, now=10, timeout=5))

    def test_device_isolation(self):
        t = SetReportTransactions()
        t.submit("a", 1, now=0, timeout=5)
        t.submit("b", 2, now=0, timeout=5)
        self.assertEqual(t.complete("b", native_status=1, now=1).request_id, 2)
        self.assertEqual(t.complete("a", native_status=0, now=1).request_id, 1)

    def test_no_unsafe_reset_api(self):
        t = SetReportTransactions()
        t.disconnect("a")
        self.assertFalse(hasattr(t, "reset_after_verified_new_session"))
        self.assertTrue(t.quarantined("a"))

    def test_reject_invalid_id_and_time(self):
        t = SetReportTransactions()
        self.assertFalse(t.submit("a", -1, now=0, timeout=5))
        self.assertFalse(t.submit("a", 0x100000000, now=0, timeout=5))
        self.assertFalse(t.submit("a", True, now=0, timeout=5))
        self.assertFalse(t.submit("a", 1, now=0, timeout=0))

if __name__ == "__main__":
    unittest.main()
