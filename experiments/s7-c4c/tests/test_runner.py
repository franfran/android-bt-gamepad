"""Mock ADB unit tests for fail-closed startup and scoped cleanup."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch, call, Mock

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

    def test_foreground_session_is_not_backgrounded(self):
        with patch.object(runner.subprocess, 'Popen') as p:
            runner.launch_foreground_session('device:1234')
        argv = p.call_args.args[0]
        self.assertEqual(argv[:7], ['adb', '-s', 'device:1234', 'exec-out', 'su', '0', 'sh'])
        self.assertIn('exec ' + runner.TARGET, argv[-1])
        self.assertNotIn(' & ', argv[-1])
        self.assertNotIn('$!', argv[-1])
        self.assertEqual(p.call_args.kwargs['stdout'], runner.subprocess.DEVNULL)

    def test_pidfile_is_from_target_and_not_shell(self):
        with patch.object(runner, 'safe_root', return_value='4242\n'):
            self.assertEqual(runner.own_pid_from_file('dev'), 4242)
        for bad in ('', '12 x', '0', '-2', '1', '123456789012345'):
            with self.subTest(value=bad), patch.object(runner, 'safe_root', return_value=bad):
                self.assertIsNone(runner.own_pid_from_file('dev'))

    def test_wait_pidfile_aborts_on_ended_session(self):
        session = Mock()
        session.poll.return_value = 23
        with patch.object(runner, 'own_pid_from_file', return_value=None):
            self.assertIsNone(runner.await_own_pid('dev', session, deadline_s=0.5))

    def test_controller_nonzero_does_not_hide_stdout(self):
        from subprocess import CompletedProcess
        result = CompletedProcess(args=['adb'], returncode=3, stdout='REMOTE CALL ERROR\n', stderr='')
        with patch.object(runner.subprocess, 'run', return_value=result), \
             patch('sys.stdout') as stdout:
            with self.assertRaisesRegex(RuntimeError, 'code 3'):
                runner.run_controller('dev')
            stdout.write.assert_any_call('REMOTE CALL ERROR')

    def test_existing_process_is_not_cleaned_up(self):
        with patch.object(runner, 'pidof_candidates', return_value=[42]), \
             patch.object(runner, 'is_owned_target', return_value=True), \
             patch.object(runner, 'cleanup') as cleanup, \
             patch.object(runner, 'adb') as adb:
            self.assertEqual(runner.run('dev'), 2)
            cleanup.assert_not_called()
            adb.assert_called_once_with('dev', 'shell', 'mkdir', '-p', runner.REMOTE)

    def test_shell_wrapper_pid_recovery(self):
        with patch.object(runner, 'pidof_candidates', return_value=[55]), \
             patch.object(runner, 'is_owned_target', side_effect=lambda _,p:p==55), \
             patch.object(runner, 'process_snapshot', return_value=self.snapshot(pid=55)):
            self.assertEqual(runner.find_target('adb', 41, deadline_s=0.5), 55)

    def test_target_writes_own_pid_before_spawning(self):
        code = (runner.BASE/'target.c').read_text()
        self.assertIn('write_own_pid()', code)
        self.assertIn('sys1(20,0)', code)  # ARM getpid, not parent shell $!
        self.assertLess(code.index('if(!write_own_pid())'), code.index('for(int i=0;i<WORKERS;i++){', code.index('_start(void)')))

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