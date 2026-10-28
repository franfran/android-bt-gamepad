#!/usr/bin/env python3
"""One-shot test-only independent process C4C-1/2 runner (NOT Bluetooth).

Runs exclusively rbxc4c_target from a fixed directory, then scoped cleanup.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
REMOTE = '/data/local/tmp/retrobox_s7c4c_test'
ARTIFACTS = ('rbxc4c_target', 'rbxc4c_controller', 'libretrobox_c4c_test.so')


def adb(serial, *args, timeout=15):
    res = subprocess.run(['adb', '-s', serial, *args], capture_output=True, text=True,
                         timeout=timeout, check=False)
    if res.returncode:
        raise RuntimeError('adb exit %s: stdout=%s stderr=%s' % (res.returncode, res.stdout.strip()[:2500], res.stderr.strip()[:300]))
    return res.stdout


def root(serial, command, timeout=15):
    return adb(serial, 'exec-out', 'su', '0', 'sh', '-c', command, timeout=timeout)


def is_owned_target(serial, pid):
    if not isinstance(pid, int) or pid <= 1:
        return False
    try:
        return root(serial, 'cat /proc/%d/comm' % pid).strip() == 'rbxc4c_target'
    except (RuntimeError, subprocess.TimeoutExpired):
        return False


def cleanup(serial, pid):
    # Never kill a process without revalidating ownership immediately before kill.
    if is_owned_target(serial, pid):
        root(serial, 'kill -9 %d' % pid)
    # This is a dedicated fixed test directory only. No Bluetooth or /system changes.
    root(serial, 'rm -rf ' + REMOTE)


def run(serial):
    pid = None
    try:
        adb(serial, 'shell', 'mkdir', '-p', REMOTE)
        for file in ARTIFACTS:
            if not (BASE / file).is_file():
                raise RuntimeError('prebuilt file not found: %s; download prebuilt package' % file)
            adb(serial, 'push', str(BASE / file), REMOTE + '/' + file)
        adb(serial, 'shell', 'chmod', '700', REMOTE + '/rbxc4c_target',
            REMOTE + '/rbxc4c_controller')
        # Redirect FDs: avoid long-running target inheriting ADB pipe.
        root(serial, 'cd ' + REMOTE + '; ./rbxc4c_target </dev/null >target.log 2>&1 & echo $! > target.pid; sleep 1')
        raw = root(serial, 'cat ' + REMOTE + '/target.pid').strip()
        if not re.fullmatch(r'[0-9]+', raw):
            raise RuntimeError('invalid target.pid; refusing ptrace')
        pid = int(raw)
        if not is_owned_target(serial, pid):
            raise RuntimeError('independently started target identity mismatch')
        result = root(serial, REMOTE + '/rbxc4c_controller', timeout=20)
        print('===== M3 S7-C4C RESULT =====')
        print(result)
        if 'PASS: non-fork independent ARM32 target' not in result:
            raise RuntimeError('No verified success marker; see controller output above')
        print('S7-C4C-1/2 INDEPENDENT TARGET = PASS (not Bluetooth authorization)')
        return 0
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print('FAIL CLOSED:', exc, file=sys.stderr)
        return 2
    finally:
        try:
            cleanup(serial, pid)
            print('TEST-ONLY CLEANUP COMPLETE')
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            print('CLEANUP WARNING:', exc, file=sys.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('adb_serial', help='ADB device serial/IP:port; no default')
    args = parser.parse_args()
    sys.exit(run(args.adb_serial))