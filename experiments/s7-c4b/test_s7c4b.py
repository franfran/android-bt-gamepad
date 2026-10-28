import unittest
from unittest.mock import patch
import s7c4b

class GateTests(unittest.TestCase):
    def setUp(self):
        self.oldelf=s7c4b.elf.elf32
        self.oldresolve=s7c4b.elf.resolve
        s7c4b.elf.elf32=lambda _: ([{}],{'dlopen':1,'android_dlopen_ext':2})
        s7c4b.elf.resolve=lambda *args: {'thumb_function_pointer':'0x1001'}
        self.maps='1000-2000 r-xp 00000000 fd:00 1 /system/lib/libbluetooth.so\n'
        self.status='Uid:\t1002\nTracerPid:\t0\nThreads:\t49\n'
    def tearDown(self):
        s7c4b.elf.elf32=self.oldelf
        s7c4b.elf.resolve=self.oldresolve
    def call(self,**changes):
        kw=dict(pid=671,comm='droid.bluetooth',status=self.status,before_maps=self.maps,after_maps=self.maps,
                first_pid='671',last_pid='671',local_bytes=b'a',remote_bytes=b'a',elf_bytes=b'ELF')
        kw.update(changes)
        return s7c4b.validate(**kw)
    def test_nominal_still_no_go(self):
        x=self.call()
        self.assertFalse(x['injection_authorized'])
        self.assertEqual(x['inspection_issues'],[])
        self.assertIn('dlopen',x['symbols'])
    def test_pid_race(self): self.assertIn('Bluetooth PID changed during validation',self.call(last_pid='672')['inspection_issues'])
    def test_mapping_race(self): self.assertIn('target mappings changed during validation',self.call(after_maps=self.maps+'extra')['inspection_issues'])
    def test_hash_mismatch(self): self.assertIn('staged add-on checksum mismatch',self.call(remote_bytes=b'bad')['inspection_issues'])
    def test_tracer(self): self.assertIn('target traced by other debugger',self.call(status=self.status.replace('TracerPid:\t0','TracerPid:\t12'))['inspection_issues'])
    def test_uid(self): self.assertIn('Bluetooth UID mismatch',self.call(status=self.status.replace('1002','2000'))['inspection_issues'])
    def test_mapped(self): self.assertIn('add-on already mapped; no retry',self.call(before_maps=self.maps+'1000-2000 r--p 00000000 fd:00 1 /data/libretrobox_ds3_addon.so\n', after_maps=self.maps+'1000-2000 r--p 00000000 fd:00 1 /data/libretrobox_ds3_addon.so\n')['inspection_issues'])
    def test_no_arbitrary_pid_input(self):
        import inspect
        self.assertNotIn('target_pid',inspect.signature(s7c4b.collect).parameters)

if __name__=='__main__':unittest.main()
