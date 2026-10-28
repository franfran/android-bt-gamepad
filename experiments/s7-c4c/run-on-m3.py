#!/usr/bin/env python3
"""S7-C4C independent ARM32 target runner, strictly NOT a Bluetooth injector.

This v2 runner diagnoses test-process startup rather than discarding target.log on
identity mismatch. It never attaches to or kills a process by unverified PID.
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
REMOTE = '/data/local/tmp/retrobox_s7c4c_test'
TARGET = REMOTE + '/rbxc4c_target'
ARTIFACTS = ('rbxc4c_target', 'rbxc4c_controller', 'libretrobox_c4c_test.so')


def adb(serial, *args, timeout=15):
    res = subprocess.run(['adb', '-s', serial, *args], capture_output=True, text=True,
                         timeout=timeout, check=False)
    if res.returncode:
        raise RuntimeError('adb exit %s: stdout=%s stderr=%s' %
                           (res.returncode, res.stdout.strip()[:800], res.stderr.strip()[:400]))
    return res.stdout


def root(serial, command, timeout=15):
    return adb(serial, 'exec-out', 'su', '0', 'sh', '-c', command, timeout=timeout)


def safe_root(serial, command):
    try:
        return root(serial, command).replace('\r', '')
    except (RuntimeError, subprocess.TimeoutExpired):
        return ''


def process_snapshot(serial, pid):
    """Collect limited /proc evidence; never use arbitrary command-supplied PID."""
    if not isinstance(pid, int) or pid <= 1:
        return {}
    prefix = '/proc/%d/' % pid
    comm = safe_root(serial, 'cat ' + prefix + 'comm').strip()
    cmdline = safe_root(serial, 'cat ' + prefix + 'cmdline').split('\0', 1)[0].strip()
    exe = safe_root(serial, 'readlink ' + prefix + 'exe').strip()
    status = safe_root(serial, 'cat ' + prefix + 'status')
    def field(key):
        match = re.search(r'^' + re.escape(key) + r':\s*(\S+)', status, re.M)
        return match.group(1) if match else ''
    return {'pid': pid, 'comm': comm, 'cmdline': cmdline, 'exe': exe,
            'uid': field('Uid'), 'threads': field('Threads'),
            'tracer': field('TracerPid'), 'state': field('State')}


def is_owned_target(serial, pid):
    """Exact executable path + root UID, not only mutable /proc/comm."""
    info = process_snapshot(serial, pid)
    return (info.get('uid') == '0' and info.get('exe') == TARGET and
            info.get('cmdline') in (TARGET, './rbxc4c_target') and
            info.get('comm') == 'rbxc4c_target')


def is_ready(info):
    return (info.get('comm') == 'rbxc4c_target' and
            info.get('tracer') == '0' and
            int(info.get('threads') or 0) >= 49)


def pidof_candidates(serial):
    raw = safe_root(serial, 'pidof rbxc4c_target || true')
    return [int(x) for x in raw.split() if x.isdecimal() and int(x) > 1]


def find_target(serial, expected, deadline_s=6):
    """Recover when Android sh backgrounds a wrapper PID instead of its exec'd child."""
    end = time.monotonic() + deadline_s
    while time.monotonic() < end:
        candidates = list(dict.fromkeys([expected] + pidof_candidates(serial)))
        owned = [pid for pid in candidates if is_owned_target(serial, pid)]
        if len(owned) == 1:
            info = process_snapshot(serial, owned[0])
            if is_ready(info):
                return owned[0]
        if len(owned) > 1:
            raise RuntimeError('multiple verified test targets; refusing ambiguous PID')
        time.sleep(0.3)
    return None


def diagnostic(serial, expected):
    print('===== S7-C4C STARTUP DIAGNOSTICS (NO PTRACE) =====', file=sys.stderr)
    print('pidfile PID:', expected, 'pidof candidates:', pidof_candidates(serial), file=sys.stderr)
    candidates = list(dict.fromkeys([expected] + pidof_candidates(serial)))
    for pid in candidates[:5]:
        info = process_snapshot(serial, pid)
        print('proc:', {k: info.get(k) for k in ('pid', 'comm', 'cmdline', 'exe',
                'uid', 'threads', 'state', 'tracer')}, file=sys.stderr)
    log = safe_root(serial, 'cat ' + REMOTE + '/target.log')[:2000].strip()
    print('target.log:', log or '(empty or unavailable)', file=sys.stderr)


def cleanup(serial, candidates):
    """Kill only independently verified, root-owned test ELF; never kill shell PID."""
    considered = set(candidates) | set(pidof_candidates(serial))
    for pid in sorted(considered):
        if is_owned_target(serial, pid):
            # Revalidate immediately before kill; do not act on stale pidfile.
            if is_owned_target(serial, pid):
                root(serial, 'kill -9 %d' % pid)
    remaining = [pid for pid in pidof_candidates(serial) if is_owned_target(serial, pid)]
    if remaining:
        print('CLEANUP WARNING: verified target remains; test dir preserved', file=sys.stderr)
    else:
        root(serial, 'rm -rf ' + REMOTE)
        print('TEST-ONLY CLEANUP COMPLETE')


def run(serial):
    candidates = set()
    try:
        adb(serial, 'shell', 'mkdir', '-p', REMOTE)
        for file in ARTIFACTS:
            if not (BASE / file).is_file():
                raise RuntimeError('missing ARM32 prebuilt: %s' % file)
            adb(serial, 'push', str(BASE / file), REMOTE + '/' + file)
        adb(serial, 'shell', 'chmod', '700', REMOTE + '/rbxc4c_target',
            REMOTE + '/rbxc4c_controller')
        # The inner shell uses exec so its background PID is the target ELF,
        # not a long-running wrapper; FDs are fully detached from ADB.
        root(serial, 'cd ' + REMOTE + '; /system/bin/sh -c '\
             "'exec " + TARGET + " </dev/null >" + REMOTE + "/target.log 2>&1' "\
             '</dev/null >/dev/null 2>&1 & echo $! > ' + REMOTE + '/target.pid; sleep 1')
        raw = root(serial, 'cat ' + REMOTE + '/target.pid').strip()
        if not re.fullmatch(r'[0-9]+', raw):
            raise RuntimeError('invalid target PID file; refusing ptrace')
        expected = int(raw)
        candidates.add(expected)
        pid = find_target(serial, expected)
        if pid is None:
            diagnostic(serial, expected)
            raise RuntimeError('independent target failed identity/readiness gate; see diagnostics')
        candidates.add(pid)
        if pid != expected:
            print('STARTUP: corrected shell-wrapper PID %d -> target PID %d' %
                  (expected, pid))
            root(serial, "printf '%d\\n' > %s/target.pid" % (pid, REMOTE))
        print('TARGET READY: PID=%d, 48 workers, identity verified' % pid)
        result = root(serial, REMOTE + '/rbxc4c_controller', timeout=25)
        print('===== M3 S7-C4C RESULT =====')
        print(result)
        if 'PASS: non-fork independent ARM32 target' not in result:
            raise RuntimeError('controller did not report complete success')
        print('S7-C4C-1/2 INDEPENDENT TARGET = PASS (NOT Bluetooth authorization)')
        return 0
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print('FAIL CLOSED:', exc, file=sys.stderr)
        return 2
    finally:
        try:
            cleanup(serial, candidates)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            print('CLEANUP WARNING:', exc, file=sys.stderr)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('adb_serial', help='ADB serial/IP:port (no default)')
    sys.exit(run(parser.parse_args().adb_serial))