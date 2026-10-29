import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ContractTests(unittest.TestCase):
    def test_controller_not_generic_injector(self):
        code=(ROOT/'controller.c').read_text()
        self.assertIn('rbxc4c_target',code)
        self.assertIn('Uid:',code)
        self.assertIn('TracerPid:',code)
        self.assertIn('Threads:',code)
        self.assertIn('STATE=QUARANTINE',code)
        self.assertNotIn('SP+256',code)
        self.assertNotIn('LR=0',code)
        self.assertNotIn('com.android.bluetooth',code)

    def test_memory_wx_and_canaries(self):
        code=(ROOT/'controller.c').read_text()
        self.assertIn('0xe1200070u',code)  # ARM BKPT encoding
        self.assertIn('0xe12fff1eu',code)  # ARM bx lr
        self.assertIn('TARGET-OWNED RX RETURN TRAMPOLINE',code)
        self.assertIn('PROT_NONE', (ROOT/'README.md').read_text())
        self.assertIn('MUNMAP',code)

    def test_exported_offsets_are_generated(self):
        values=re.findall(r'#define OFF_(RBXC4C_[A-Z0-9_]+) 0x([0-9A-F]{8})u',
                          (ROOT/'target_offsets.h').read_text())
        self.assertGreaterEqual(len(values),8)
        self.assertEqual(len(values),len(set(n for n,_ in values)))
        self.assertTrue(all(int(v,16)>0 for _,v in values))

    def test_runner_only_kills_validated_test_name(self):
        runner=(ROOT/'run-on-m3.py').read_text()
        self.assertIn('is_owned_target(serial, pid)',runner)
        self.assertIn("== 'rbxc4c_target'",runner)
        self.assertNotIn('killall',runner)
        self.assertNotIn('stop bluetooth',runner)

    def test_svc_bootstrap_does_not_call_precompiled_trap(self):
        code=(ROOT/'controller.c').read_text()
        self.assertIn('instruction==0xef000000u',code)
        self.assertIn('PTRACE_TRACESYSGOOD',code)
        self.assertIn('SYSCALL_STOP (SIGTRAP|0x80)',code)
        self.assertIn('static int remote_syscall(',code)
        self.assertIn('remote_syscall(pid,&orig,svc,192,args',code)
        self.assertIn('remote_syscall(pid,&orig,svc,125,args',code)
        self.assertIn('remote_syscall(pid,&orig,svc,91,args',code)
        self.assertNotIn('OFF_RBXC4C_RETURN_TRAP',code)
        self.assertNotIn('OFF_RBXC4C_MMAP2',code)
        self.assertNotIn('OFF_RBXC4C_MPROTECT',code)
        self.assertNotIn('OFF_RBXC4C_MUNMAP',code)
        self.assertIn('STATE=QUARANTINE',code)
        # Bootstrap must scan existing executable text, not replace a text word.
        self.assertIn("maps_buf[j]!='r'||maps_buf[j+2]!='x'",code)
        self.assertNotIn('poke(pid,svc',code)

    def test_syscall_bootstrap_calls_restore_original_registers(self):
        code=(ROOT/'controller.c').read_text()
        start=code.index('static int remote_syscall(')
        stop=code.index('static int remote_call(',start)
        bootstrap=code[start:stop]
        self.assertIn('SETREGS,pid,0,(int)orig',bootstrap)
        self.assertIn('stop.r[i]!=orig->r[i]',bootstrap)
        self.assertIn('if(waitstop(pid,timeout,&status)!=1',bootstrap)
        self.assertIn('WSTOPSIG(status)!=SYSCALL_STOP',bootstrap)

    def test_no_vendor_binary_in_build(self):
        build=(ROOT/'build-sandbox.sh').read_text()
        self.assertIn('test_addon.c',build)
        self.assertIn('target.c',build)
        self.assertIn('controller.c',build)
        self.assertIn('readelf',build)

if __name__=='__main__':unittest.main()