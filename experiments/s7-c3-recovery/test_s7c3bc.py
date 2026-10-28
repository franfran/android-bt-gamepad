import unittest
from unittest.mock import patch
from s7c3bc import CallSafety, Phase, inspect
class TestStateMachine(unittest.TestCase):
    def test_normal(self):
        s=CallSafety()
        for event in ('identity_ok','remote_mmap_ok','arguments_verified','enter_dlopen','dlopen_returned','remote_munmap_ok','registers_verified','detach_verified'):
            self.assertTrue(s.step(event))
        self.assertEqual(s.phase,Phase.CLOSED)
        self.assertFalse(s.result()['bluetooth_injection_authorized'])
    def test_linker_timeout_is_quarantine(self):
        s=CallSafety()
        for event in ('identity_ok','remote_mmap_ok','arguments_verified','enter_dlopen'):s.step(event)
        self.assertFalse(s.step('timeout'))
        self.assertEqual(s.phase,Phase.QUARANTINE)
        self.assertTrue(s.restart_required)
        self.assertFalse(s.step('dlopen_returned'))
    def test_prelinker_timeout_not_claimed_recovered(self):
        s=CallSafety();s.step('identity_ok');s.step('timeout')
        self.assertEqual(s.phase,Phase.QUARANTINE)
        self.assertFalse(s.result()['safe_to_retry'])
    def test_out_of_order_fails_closed(self):
        s=CallSafety();self.assertFalse(s.step('enter_dlopen'))
        self.assertEqual(s.phase,Phase.QUARANTINE)
    def test_lost_tracer_quarantines(self):
        s=CallSafety();s.step('identity_ok');s.step('remote_mmap_ok');s.step('arguments_verified');s.step('enter_dlopen')
        self.assertFalse(s.step('tracer_lost'));self.assertTrue(s.restart_required)
    @patch('s7c3bc.shell_adb')
    def test_live_snapshot_readonly_rules(self,m):
        def fake(_,cmd):
            if cmd.startswith('pidof'):return '675'
            if cmd.endswith('/comm'):return 'droid.bluetooth'
            if cmd.endswith('/status'):return 'Name:\tdroid.bluetooth\nUid:\t1002 1002 1002 1002\nTracerPid:\t0\nThreads:\t2\nSeccomp:\t0'
            if cmd.endswith('/task'):return '675\n676'
            return '/apex/com.android.runtime/lib/bionic/libdl.so\n/apex/com.android.runtime/bin/linker\n/system/lib/libbluetooth.so'
        m.side_effect=fake
        r=inspect('fake')
        self.assertEqual(r['issues'],[])
        self.assertFalse(r['bluetooth_injection_authorized'])
    @patch('s7c3bc.shell_adb')
    def test_pid_change_detected(self,m):
        n=0
        def fake(_,cmd):
            nonlocal n
            if cmd.startswith('pidof'):
                n+=1;return '675' if n==1 else '676'
            if cmd.endswith('/comm'):return 'droid.bluetooth'
            if cmd.endswith('/status'):return 'Uid:\t1002\nTracerPid:\t0\nThreads:\t1\nSeccomp:\t0'
            if cmd.endswith('/task'):return '675'
            return '/apex/com.android.runtime/lib/bionic/libdl.so\n/apex/com.android.runtime/bin/linker\n/system/lib/libbluetooth.so'
        m.side_effect=fake
        self.assertIn('PID changed during snapshot',inspect('fake')['issues'])
if __name__=='__main__':unittest.main()
