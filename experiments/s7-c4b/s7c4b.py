#!/usr/bin/env python3
"""S7-C4B: single-snapshot Bluetooth target resolver and add-on integrity integration.

Read-only: cannot ptrace, modify registers, remotely call dlopen or inject.
Fails closed; never authorizes Bluetooth injection.
"""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
import s7c3_resolver as elf

REMOTE = '/data/local/tmp/retrobox_s7c4_inert/libretrobox_ds3_addon.so'
LOCAL = Path(__file__).with_name('libretrobox_ds3_addon.so')


def device_output(serial, cmd, binary=False):
    # No external PID or arbitrary command accepted from users.
    result = subprocess.run(['adb', '-s', serial, 'exec-out', 'su', '0', 'sh', '-c', cmd],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    if result.returncode:
        raise RuntimeError('ADB read failed: ' + result.stderr.decode(errors='replace')[:200])
    return result.stdout if binary else result.stdout.decode(errors='replace').replace('\r','').replace('\x00','')


def validate(pid, comm, status, before_maps, after_maps, first_pid, last_pid,
             local_bytes, remote_bytes, elf_bytes):
    issues=[]
    rows=elf.maps_parse(before_maps)
    uid=re.search(r'^Uid:\s+(\d+)',status,re.M)
    tracer=re.search(r'^TracerPid:\s+(\d+)',status,re.M)
    threadcount=re.search(r'^Threads:\s+(\d+)',status,re.M)
    if comm.strip() != 'droid.bluetooth': issues.append('process identity changed')
    if not uid or uid[1] != '1002': issues.append('Bluetooth UID mismatch')
    if not tracer or tracer[1] != '0': issues.append('target traced by other debugger')
    if first_pid != last_pid or str(pid) != first_pid: issues.append('Bluetooth PID changed during validation')
    if before_maps != after_maps: issues.append('target mappings changed during validation')
    if local_bytes != remote_bytes: issues.append('staged add-on checksum mismatch')
    if not any('/system/lib/libbluetooth.so' == r['path'] for r in rows): issues.append('libbluetooth.so not mapped')
    if any('libretrobox_ds3_addon.so' in r['path'] for r in rows): issues.append('add-on already mapped; no retry')
    syms={}
    try:
        loads, symbols=elf.elf32(elf_bytes)
        for name in ('dlopen','android_dlopen_ext'):
            if name not in symbols: raise ValueError('missing ELF symbol '+name)
            syms[name]=elf.resolve(rows,loads,symbols[name])
    except ValueError as e:
        issues.append('ELF address verification failed: '+str(e))
    return {'stage':'S7-C4B', 'mode':'READ_ONLY_INTEGRATION',
            'target':{'pid':pid,'uid':int(uid[1]) if uid else None,
                      'threads':int(threadcount[1]) if threadcount else None,
                      'tracerpid':int(tracer[1]) if tracer else None},
            'addon':{'path':REMOTE,'sha256':hashlib.sha256(remote_bytes).hexdigest(),
                     'matches_local':local_bytes==remote_bytes,'mapped':any('libretrobox_ds3_addon.so' in r['path'] for r in rows)},
            'libdl_sha256':hashlib.sha256(elf_bytes).hexdigest(),
            'symbols':syms,'inspection_issues':issues,
            'injection_authorized':False,
            'blockers': issues + [
              'No tested safe return trampoline for an already-running Android Bluetooth process',
              'Linker namespace acceptance cannot be verified without executing inside target',
              'Interrupted linker call cannot be safely rolled back by restoring registers',
              'No approved service-recovery procedure for failed target dlopen']}


def collect(serial):
    pidtext=device_output(serial,'pidof com.android.bluetooth').strip()
    if not re.fullmatch(r'[0-9]+',pidtext): raise RuntimeError('Bluetooth PID missing or ambiguous')
    pid=int(pidtext)
    # Read from the currently running target; never trust previous saved addresses/PIDs.
    comm=device_output(serial,f'cat /proc/{pid}/comm')
    status=device_output(serial,f'cat /proc/{pid}/status')
    maps=device_output(serial,f'cat /proc/{pid}/maps')
    remote=device_output(serial,f'cat {REMOTE}',binary=True)
    lib=device_output(serial,f'cat {elf.LIB}',binary=True)
    aftermaps=device_output(serial,f'cat /proc/{pid}/maps')
    afterpid=device_output(serial,'pidof com.android.bluetooth').strip()
    return validate(pid,comm,status,maps,aftermaps,pidtext,afterpid,LOCAL.read_bytes(),remote,lib)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('serial',help='M3 ADB serial, e.g. 192.0.2.10:1080')
    p.add_argument('--output',type=Path,default=Path('s7c4b-evidence.json'))
    args=p.parse_args()
    try:
        result=collect(args.serial)
    except (RuntimeError,OSError,subprocess.TimeoutExpired,ValueError) as e:
        result={'stage':'S7-C4B','mode':'READ_ONLY_INTEGRATION',
                'injection_authorized':False,'inspection_issues':[str(e)],
                'blockers':['Fail-closed: '+str(e)]}
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2,sort_keys=True))
    print('INJECTION_GATE=NO-GO (no injection code is included)')
    return 2 if result['inspection_issues'] else 0

if __name__=='__main__': sys.exit(main())
