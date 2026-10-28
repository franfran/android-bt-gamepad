"""Mock ADB unit tests for fail-closed startup and scoped cleanup."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch, call

SRC = Path(__file__).resolve().parents[1] / 'run-on-m3.py'
spec = importlib.util.spec_from_file_location('rbxc4c_runner', SRC)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class RunnerTests(unittest.TestCase):
    def snapshot(self, **kw):
        value = {'pid': 41, 'comm': 'rbxc4c_target', 'cmdline': runner.TARGET,
                 'exe': runner.TARGET, 'uid': '0', 'threads': '49',
                 'tracer': '0', 'state': 'S'}
        value.update(kw)
        return value

    def test_owned_target_needs_uid_path_cmdline_and_name(self):
        with patch.object(runner, 'process_snapshot', return_value=self.snapshot()):
            self.assertTrue(runner.is_owned_target('adb', 41))
        for change in ({'uid':'1002'}, {'exe':'/system/bin/sh'},
                       {'cmdline':'/system/bin/sh'}, {'comm':'sh'}):
            with self.subTest(change=change), patch.object(runner, 'process_snapshot',
                    return_value=self.snapshot(**change)):
                self.assertFalse(runner.is_owned_target('adb', 41))

    def test_ready_needs_worker_count_and_no_tracer(self):
        self.assertTrue(runner.is_ready(self.snapshot()))
        self.assertFalse(runner.is_ready(self.snapshot(threads='48')))
        self.assertFalse(runner.is_ready(self.snapshot(tracer='14')))
        self.assertFalse(runner.is_ready(self.snapshot(comm='sh')))

    def test_shell_wrapper_pid_recovery(self):
        with patch.object(runner, 'pidof_candidates', return_value=[55]), \
             patch.object(runner, 'is_owned_target', side_effect=lambda _,p:p==55), \
             patch.object(runner, 'process_snapshot', return_value=self.snapshot(pid=55)):
            self.assertEqual(runner.find_target('adb', 41, deadline_s=0.5), 55)

    def test_cleanup_does_not_kill_unverified_process(self):
        with patch.object(runner, 'pidof_candidates', return_value=[]), \
             patch.object(runner, 'is_owned_target', return_value=False), \
             patch.object(runner, 'root') as root:
            runner.cleanup('adb', {41})
            self.assertEqual(root.call_args_list, [call('adb', 'rm -rf ' + runner.REMOTE)])

    def test_cleanup_kills_only_validated_target(self):
        with patch.object(runner, 'pidof_candidates', return_value=[]), \
             patch.object(runner, 'is_owned_target', side_effect=lambda _,p:p==55), \
             patch.object(runner, 'root') as root:
            runner.cleanup('adb', {41,55})
            self.assertEqual(root.call_args_list, [call('adb', 'kill -9 55'),
                                                  call('adb', 'rm -rf ' + runner.REMOTE)])

if __name__ == '__main__':
    unittest.main()