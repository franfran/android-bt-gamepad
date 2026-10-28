#!/usr/bin/env python3
"""RetroBox S6: read-only Bluetooth production injection safety gate.
No ptrace, no file push, no root filesystem modifications, no remote calls.
"""
import argparse
import re
import subprocess
import sys
from collections import Counter


def adb(device, command):
    p = subprocess.run(['adb', '-s', device, 'shell', command], capture_output=True,
                       text=True, timeout=12)
    if p.returncode:
        raise RuntimeError(f'adb shell failed: {command}\n{p.stderr.strip()}')
    return p.stdout.replace('\r', '').strip()


def root(device, command):
    return adb(device, f'su 0 {command}')


def fields(text):
    return dict(re.findall(r'^([A-Za-z][A-Za-z0-9_]*):[ \t]*(.*)$', text, re.M))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', help='ADB device, e.g. 192.0.2.10:1080')
    a = parser.parse_args()
    print('=== RetroBox S6 — BLUETOOTH INERT ADD-ON SAFETY GATE (READ ONLY) ===')
    print('No attach, memory write, system change, file upload or injection.')
    try:
        pidstr = adb(a.device, 'pidof com.android.bluetooth').split()
        if len(pidstr) != 1 or not pidstr[0].isdigit():
            raise RuntimeError('Bluetooth PID ambiguous or missing')
        pid = int(pidstr[0])
        status = root(a.device, f'cat /proc/{pid}/status')
        ps = fields(status)
        comm = root(a.device, f'cat /proc/{pid}/comm')
        context = root(a.device, f'cat /proc/{pid}/attr/current')
        maps = root(a.device, f'cat /proc/{pid}/maps')
        tids = root(a.device, f'ls /proc/{pid}/task').split()
        uid = ps.get('Uid', '').split()
        tstates = Counter()
        problems = []
        for tid in tids:
            if not tid.isdigit():
                problems.append(f'Unexpected thread identifier {tid!r}')
                continue
            ts = fields(root(a.device, f'cat /proc/{pid}/task/{tid}/status'))
            state = ts.get('State', '?')
            tstates[state.split()[0]] += 1
            tracer = ts.get('TracerPid', '?')
            if tracer != '0':
                problems.append(f'TID {tid} unexpectedly traced (TracerPid={tracer})')
        pid_after = adb(a.device, 'pidof com.android.bluetooth')
        libs = {
            'libdl': '/libdl.so', 'libc': '/libc.so',
            'linker': '/bin/linker', 'Bluetooth native': '/libbluetooth.so',
            'addon (already mapped)': 'libretrobox_ds3_addon.so'
        }
        matches = {}
        for key, suffix in libs.items():
            matches[key] = [line.strip() for line in maps.splitlines() if suffix in line]
        if comm != 'droid.bluetooth':
            problems.append(f'Unexpected process name: {comm!r}')
        if len(uid) < 4 or any(x != '1002' for x in uid[:4]):
            problems.append(f'Unexpected UID fields: {uid}')
        if ps.get('TracerPid') != '0':
            problems.append('Bluetooth leader is currently traced')
        if pid_after != str(pid):
            problems.append('Bluetooth process changed during observation')
        if not matches['libdl'] or not matches['linker'] or not matches['Bluetooth native']:
            problems.append('Required native library mappings are missing')
        if matches['addon (already mapped)']:
            problems.append('Inert addon already mapped; do not reinject')
        print(f'PID={pid}; PID_AFTER={pid_after}; COMM={comm}; SELINUX_CONTEXT={context}')
        print(f'UID={ps.get("Uid", "?")}; TracerPid={ps.get("TracerPid", "?")}; Seccomp={ps.get("Seccomp", "?")}')
        print(f'REPORTED_THREADS={ps.get("Threads", "?")}; ENUMERATED_THREADS={len(tids)}')
        print('THREAD_STATES=' + repr(dict(sorted(tstates.items()))))
        for key in libs:
            print(f'[{key}]')
            for line in matches[key][:8]:
                print('  ' + line)
            if len(matches[key]) > 8:
                print(f'  ... {len(matches[key])-8} more')
        if problems:
            print('OBSERVATION PROBLEMS:')
            for x in problems:
                print(' - ' + x)
        else:
            print('OBSERVATION: identity, mappings and tracer state consistent.')
        print('INJECTION GATE: NO-GO (by design).')
        print('REASON: linker-lock recovery, target-specific scratch, namespace acceptance,')
        print('        and bounded failure handling have NOT been demonstrated in Bluetooth.')
        print('NEVER use the obsolete D2b-2d-B inject binary.')
        print('PASS: read-only audit completed.' if not problems else 'FAIL: read-only audit found inconsistencies.')
        return 0 if not problems else 2
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as ex:
        print('FAIL: ' + str(ex), file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
