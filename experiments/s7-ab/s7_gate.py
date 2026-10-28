#!/usr/bin/env python3
"""RetroBox S7-A/B: fail-closed read-only integration gate. NEVER injects."""
import argparse, re, subprocess, sys, json, hashlib
from pathlib import Path

def adb(serial, cmd, timeout=15):
    r=subprocess.run(['adb','-s',serial,'shell',cmd],text=True,capture_output=True,timeout=timeout)
    if r.returncode: raise RuntimeError(f'adb {cmd}: {r.stderr.strip()}')
    return r.stdout.replace('\r','').replace('\x00','').strip()

def root(serial, cmd): return adb(serial,'su 0 '+cmd)
def parse_maps(data):
    rows=[]
    for line in data.splitlines():
        m=re.match(r'^([0-9a-f]+)-([0-9a-f]+)\s+([rwxps-]{4})\s+([0-9a-f]+)\s+\S+\s+\d+\s*(.*)$',line)
        if m: rows.append(dict(start=int(m[1],16),end=int(m[2],16),perms=m[3],offset=int(m[4],16),path=m[5].strip()))
    return rows

def inspect_legacy_source(source):
    findings=[]
    if 'original.r[13]+256u' in source or 'original.r[13] + 256' in source:
        findings.append('BLOCKER: uses interrupted Bluetooth SP+256 as scratch')
    if 'sc4(114,pid,(int)&st,0,0)' in source:
        findings.append('BLOCKER: potentially unbounded blocking wait4 on remote dlopen')
    if 'modified.r[14]=0' in source or 'modified.r[14] = 0' in source:
        findings.append('BLOCKER: uses NULL return address in target process')
    if 'int v=sc4(26,2,pid,' in source:
        findings.append('BLOCKER: raw PTRACE_PEEKDATA treats syscall return as word')
    return findings

def analyze(maps_text, status, comm, tids, after, pid):
    rows=parse_maps(maps_text)
    get=lambda n:[x for x in rows if x['path'].endswith(n)]
    libs={n:get(n) for n in ('/libdl.so','/libc.so','/libbluetooth.so','/bin/linker')}
    concerns=[]
    uid=re.search(r'^Uid:\s+(\d+)',status,re.M)
    tracer=re.search(r'^TracerPid:\s+(\d+)',status,re.M)
    threads=re.search(r'^Threads:\s+(\d+)',status,re.M)
    if comm!='droid.bluetooth': concerns.append('process identity mismatch')
    if not uid or uid[1]!='1002': concerns.append('Bluetooth UID mismatch')
    if not tracer or tracer[1]!='0': concerns.append('process already traced')
    if not threads or int(threads[1])!=len(tids): concerns.append('thread-count mismatch')
    if str(pid)!=after: concerns.append('PID changed during snapshot')
    for name,vals in libs.items():
        if not vals: concerns.append(f'missing expected {name} mapping')
        elif not any('x' in x['perms'] for x in vals): concerns.append(f'missing executable {name} mapping')
    if any('libretrobox_ds3_addon.so' in x['path'] for x in rows): concerns.append('addon already present')
    detail={}
    for name, vals in libs.items():
        detail[name]=[{'start':hex(x['start']),'end':hex(x['end']),'perms':x['perms'],'file_offset':hex(x['offset']),'path':x['path']} for x in vals]
    return concerns,detail

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('device', nargs='?', help='ADB serial e.g. 192.0.2.10:1080')
    p.add_argument('--source',type=Path,help='Optional local legacy injector C source for static rejection audit')
    p.add_argument('--fixture',type=Path,help='Analyze a saved S6 report offline (never ADB)')
    p.add_argument('--json-out',type=Path,help='Write machine readable evidence')
    a=p.parse_args()
    if not a.device and not a.fixture:p.error('provide DEVICE or --fixture')
    print('=== RetroBox S7-A/B fail-closed integration assessment ===')
    print('MODE=READ_ONLY; NO PTRACE; NO FILE PUSH; NO INJECTION')
    result={'version':'s7-ab-v1','injection_authorized':False,'checks':{},'blockers':[]}
    if a.source:
        content=a.source.read_text()
        findings=inspect_legacy_source(content)
        result['checks']['source_sha256']=hashlib.sha256(content.encode()).hexdigest()
        result['checks']['source_hazards']=findings
        result['blockers']+=findings
    if a.fixture:
        txt=a.fixture.read_text(errors='replace')
        checks={'pid':re.search(r'PID=(\d+)',txt),'reported':re.search(r'REPORTED_THREADS=(\d+); ENUMERATED_THREADS=(\d+)',txt),'tracer':re.search(r'TracerPid=(\d+)',txt)}
        result['checks']['fixture']={k: v.groups() if v else None for k,v in checks.items()}
        if any(v is None for v in result['checks']['fixture'].values()):result['blockers'].append('incomplete fixture')
        if checks['reported'] and checks['reported'][1]!=checks['reported'][2]:result['blockers'].append('thread enumeration mismatch')
    else:
        try:
            serial=a.device
            ps=adb(serial,'pidof com.android.bluetooth').split()
            if len(ps)!=1 or not ps[0].isdigit():raise RuntimeError('PID ambiguous')
            pid=int(ps[0]); status=root(serial,f'cat /proc/{pid}/status'); comm=root(serial,f'cat /proc/{pid}/comm')
            maps=root(serial,f'cat /proc/{pid}/maps'); tids=root(serial,f'ls /proc/{pid}/task').split()
            after=adb(serial,'pidof com.android.bluetooth')
            problems,libs=analyze(maps,status,comm,tids,after,pid)
            result['checks'].update({'pid':pid,'threads':len(tids),'library_mappings':libs})
            result['blockers']+=problems
            print(f'BLUETOOTH_PID={pid} THREADS={len(tids)}')
            for k,vals in libs.items():print(f'{k}: '+(', '.join(x['start']+' '+x['perms']+' '+x['path'] for x in vals) or 'MISSING'))
            print('LINKER_NAMESPACE_POLICY=UNKNOWN (cannot establish from maps alone)')
        except (OSError,subprocess.TimeoutExpired,RuntimeError) as e:
            result['blockers'].append('snapshot failed: '+str(e))
    # These remain blockers until there is a separately reviewed target-specific implementation and evidence.
    result['blockers'] += [
      'No audited target-owned remote mmap/munmap lifecycle integrated into Bluetooth loader',
      'No demonstrated safe recovery from linker-lock contention in Bluetooth process',
      'No demonstrated namespace acceptance for injected addon in Bluetooth process',
      'No independently validated failure recovery following interrupted remote dlopen',
    ]
    for x in result['blockers']:print('BLOCKER:',x)
    print('INJECTION_GATE=NO-GO')
    if a.json_out:
        a.json_out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print('EVIDENCE_WRITTEN='+str(a.json_out))
    return 0 if not any(x.startswith('snapshot failed') for x in result['blockers']) else 2
if __name__=='__main__':sys.exit(main())
