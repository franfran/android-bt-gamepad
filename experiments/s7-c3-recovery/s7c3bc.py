#!/usr/bin/env python3
"""RetroBox S7-C3b/c: Bluetooth-specific fail-closed integration contract.
No ptrace, remote calls, writes, library loading, or injection paths exist here.
"""
import argparse, dataclasses, enum, json, re, subprocess, sys
from pathlib import Path

class Phase(str, enum.Enum):
    NEW='NEW'; IDENTITY_CHECKED='IDENTITY_CHECKED'; SCRATCH_ALLOCATED='SCRATCH_ALLOCATED'
    ARGUMENTS_VERIFIED='ARGUMENTS_VERIFIED'; DLOPEN_ENTERED='DLOPEN_ENTERED'
    DLOPEN_RETURNED='DLOPEN_RETURNED'; SCRATCH_RELEASED='SCRATCH_RELEASED'
    RESTORED='RESTORED'; CLOSED='CLOSED'; QUARANTINE='QUARANTINE'

@dataclasses.dataclass
class CallSafety:
    phase: Phase=Phase.NEW
    stop_reason: str=''
    restart_required: bool=False
    def step(self, event):
        transitions={
          (Phase.NEW,'identity_ok'):Phase.IDENTITY_CHECKED,
          (Phase.IDENTITY_CHECKED,'remote_mmap_ok'):Phase.SCRATCH_ALLOCATED,
          (Phase.SCRATCH_ALLOCATED,'arguments_verified'):Phase.ARGUMENTS_VERIFIED,
          (Phase.ARGUMENTS_VERIFIED,'enter_dlopen'):Phase.DLOPEN_ENTERED,
          (Phase.DLOPEN_ENTERED,'dlopen_returned'):Phase.DLOPEN_RETURNED,
          (Phase.DLOPEN_RETURNED,'remote_munmap_ok'):Phase.SCRATCH_RELEASED,
          (Phase.SCRATCH_RELEASED,'registers_verified'):Phase.RESTORED,
          (Phase.RESTORED,'detach_verified'):Phase.CLOSED,
        }
        if self.phase in (Phase.QUARANTINE,Phase.CLOSED):return False
        if event in ('timeout','unexpected_stop','tracer_lost','pid_changed','unverified_state'):
            self.stop_reason=event
            # Once dlopen has been entered, the linker may retain locks or partial state.
            self.restart_required=self.phase in (Phase.DLOPEN_ENTERED,Phase.DLOPEN_RETURNED)
            self.phase=Phase.QUARANTINE
            return False
        nxt=transitions.get((self.phase,event))
        if nxt is None:
            self.stop_reason='invalid transition: '+self.phase.value+' -> '+event
            self.phase=Phase.QUARANTINE
            return False
        self.phase=nxt
        return True
    def result(self):
        return {'phase':self.phase.value,'stop_reason':self.stop_reason,
                'restart_required':self.restart_required,'safe_to_retry':False,
                'bluetooth_injection_authorized':False}

def shell_adb(device,cmd):
    p=subprocess.run(['adb','-s',device,'shell','su 0 '+cmd],capture_output=True,timeout=15)
    if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[:300])
    return p.stdout.decode(errors='replace').replace('\r','').replace('\x00','').strip()

def inspect(device, prev=None):
    pid_str=shell_adb(device,'pidof com.android.bluetooth')
    if not re.fullmatch(r'\d+',pid_str):raise ValueError('pidof returned unexpected value')
    pid=int(pid_str)
    comm=shell_adb(device,f'cat /proc/{pid}/comm')
    status=shell_adb(device,f'cat /proc/{pid}/status')
    tasks=shell_adb(device,f'ls /proc/{pid}/task')
    maps=shell_adb(device,f'cat /proc/{pid}/maps')
    after=shell_adb(device,'pidof com.android.bluetooth')
    get=lambda key: re.search(r'^'+re.escape(key)+r':\s*([^\n]+)',status,re.M)
    uid=get('Uid'); tracer=get('TracerPid'); threads=get('Threads'); seccomp=get('Seccomp')
    reasons=[]
    if comm!='droid.bluetooth':reasons.append('wrong process name')
    if not uid or uid[1].split()[0]!='1002':reasons.append('wrong UID')
    if not tracer or tracer[1].split()[0]!='0':reasons.append('unexpected tracing')
    if not seccomp or seccomp[1].split()[0]!='0':reasons.append('unexpected seccomp')
    tids=re.findall(r'^\d+$',tasks,re.M)
    if not threads or len(tids)!=int(threads[1].split()[0]):reasons.append('thread count changed during snapshot')
    if after!=pid_str:reasons.append('PID changed during snapshot')
    if prev and prev.get('pid')!=pid:reasons.append('PID changed since address snapshot')
    if 'libretrobox_ds3_addon.so' in maps:reasons.append('addon already present')
    for path in ('/apex/com.android.runtime/lib/bionic/libdl.so','/apex/com.android.runtime/bin/linker','/system/lib/libbluetooth.so'):
        if path not in maps:reasons.append('missing '+path)
    return {'stage':'S7-C3b/c','mode':'READ_ONLY','pid':pid,'thread_count':len(tids),
        'uid':uid[1].split()[0] if uid else None,'tracerpid':tracer[1].split()[0] if tracer else None,
        'issues':reasons,'persistent_blockers':[
          'No safe proof that injected dlopen can recover from linker-lock contention',
          'Bluetooth linker namespace acceptance untested',
          'Actual remote mmap/dlopen lifecycle in Bluetooth not validated'],
        'bluetooth_injection_authorized':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('device',nargs='?')
    p.add_argument('--output',default='s7c3bc-evidence.json')
    p.add_argument('--scenario',choices=('normal','timeout-before-linker','timeout-during-linker','unexpected-stop'))
    a=p.parse_args()
    if not a.device and not a.scenario:p.error('provide DEVICE or --scenario')
    if a.scenario:
        sm=CallSafety()
        events=['identity_ok','remote_mmap_ok','arguments_verified']
        if a.scenario=='normal':events+=['enter_dlopen','dlopen_returned','remote_munmap_ok','registers_verified','detach_verified']
        elif a.scenario=='timeout-before-linker':events+=['timeout']
        elif a.scenario=='timeout-during-linker':events+=['enter_dlopen','timeout']
        else:events+=['enter_dlopen','unexpected_stop']
        for ev in events:sm.step(ev)
        result={'scenario':a.scenario,**sm.result()}
    else:
        try:result=inspect(a.device)
        except (RuntimeError,ValueError,OSError,subprocess.TimeoutExpired) as exc:
            result={'stage':'S7-C3b/c','mode':'READ_ONLY','issues':[str(exc)],'bluetooth_injection_authorized':False}
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2,sort_keys=True))
    print('INJECTION_GATE=NO-GO')
    return 0
if __name__=='__main__':sys.exit(main())
