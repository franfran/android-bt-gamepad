#!/usr/bin/env python3
"""RetroBox S7-C4A: stage/verify inert addon; NEVER inject or ptrace Bluetooth."""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path

REMOTE='/data/local/tmp/retrobox_s7c4_inert'
LOCAL=Path(__file__).with_name('libretrobox_ds3_addon.so')
UPLOAD='/data/local/tmp/retrobox_s7c4_inert_upload.so'

def call(args, timeout=20):
    p=subprocess.run(args, capture_output=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError(f'command failed ({p.returncode}): {args[:4]}: '+p.stderr.decode(errors='replace')[-400:])
    return p.stdout.decode(errors='replace').replace('\r','').replace('\x00','')

def shell(serial, cmd):
    # All commands here are fixed, without user-supplied shell fragments.
    return call(['adb','-s',serial,'shell','su 0 '+cmd])

def sha256(data): return hashlib.sha256(data).hexdigest()

def run(serial, action):
    result={'stage':'S7-C4A','mode':action,'injection_authorized':False,
            'remote_dir':REMOTE,'checks':{},'blockers':[
            'Bluetooth runtime dlopen remains untested',
            'Android linker namespace acceptance cannot be proven outside the target process',
            'Safely resuming interrupted target linker call is not demonstrated']}
    if action=='stage':
        if not LOCAL.is_file():raise RuntimeError('missing inert add-on from package')
        # adb push runs as shell UID 2000, while su-created directories may
        # be root-owned. Upload to shell-writable /data/local/tmp first, then
        # use root to copy into the dedicated staging directory. Avoid chmod
        # entirely: on this firmware chmod under /data/local/tmp can fail EPERM.
        try:
            call(['adb','-s',serial,'push',str(LOCAL),UPLOAD])
            shell(serial, 'mkdir -p '+REMOTE+' && cp '+UPLOAD+' '+REMOTE+'/libretrobox_ds3_addon.so')
        finally:
            # Remove our temporary upload even if root copy fails.
            subprocess.run(['adb','-s',serial,'shell','rm -f '+UPLOAD],
                           capture_output=True, timeout=20)
    elif action=='cleanup':
        shell(serial, 'rm -f '+REMOTE+'/libretrobox_ds3_addon.so && rmdir '+REMOTE)
        subprocess.run(['adb','-s',serial,'shell','rm -f '+UPLOAD],
                       capture_output=True, timeout=20)
        result['checks']['staging_removed']=True
        return result
    pid=shell(serial,'pidof com.android.bluetooth').strip()
    if not re.fullmatch(r'\d+',pid):raise RuntimeError('Bluetooth PID missing/ambiguous')
    status=shell(serial,'cat /proc/'+pid+'/status')
    uid=re.search(r'^Uid:\s+(\d+)',status,re.M)
    tracer=re.search(r'^TracerPid:\s+(\d+)',status,re.M)
    threads=re.search(r'^Threads:\s+(\d+)',status,re.M)
    name=shell(serial,'cat /proc/'+pid+'/comm').strip()
    if name!='droid.bluetooth' or not uid or uid.group(1)!='1002' or not tracer or tracer.group(1)!='0':
        raise RuntimeError('Bluetooth identity or tracer state changed; refuse')
    result['checks'].update(pid=int(pid),uid=1002,tracerpid=0,threads=int(threads.group(1)) if threads else None)
    addon=REMOTE+'/libretrobox_ds3_addon.so'
    try:
        p=subprocess.run(['adb','-s',serial,'exec-out','su','0','cat',addon],capture_output=True,timeout=30)
        if p.returncode:raise RuntimeError('remote addon unreadable')
        remote_bytes=p.stdout
        expected=LOCAL.read_bytes()
        result['checks']['addon_sha256']=sha256(remote_bytes)
        result['checks']['addon_matches_local']=remote_bytes==expected
        if not result['checks']['addon_matches_local']:raise RuntimeError('addon checksum mismatch')
        result['checks']['addon_size']=len(remote_bytes)
    except (OSError,RuntimeError) as e:
        result['checks']['addon_error']=str(e)
        if action=='stage':raise
    maps=shell(serial,'cat /proc/'+pid+'/maps')
    result['checks']['already_mapped']=any(REMOTE in line for line in maps.splitlines())
    result['checks']['libdl_mapped']=('/apex/com.android.runtime/lib/bionic/libdl.so' in maps)
    result['checks']['bluetooth_library_mapped']=('/system/lib/libbluetooth.so' in maps)
    after=shell(serial,'pidof com.android.bluetooth').strip()
    result['checks']['pid_unchanged']=after==pid
    if not result['checks']['pid_unchanged']:raise RuntimeError('PID changed during inspection')
    if result['checks']['already_mapped']:result['blockers'].append('Add-on already mapped: unexpected prior injection; do not retry')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('device');ap.add_argument('action',choices=['stage','check','cleanup']);ap.add_argument('--output',default='s7c4a-evidence.json')
    a=ap.parse_args()
    try:
        evidence=run(a.device,a.action)
        Path(a.output).write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
        print(json.dumps(evidence,indent=2,sort_keys=True))
        print('RESULT: STAGING ONLY; NO INJECTION IMPLEMENTED')
    except Exception as e:
        print('FAIL CLOSED:',e,file=sys.stderr);sys.exit(2)
