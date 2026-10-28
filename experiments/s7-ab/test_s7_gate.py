import unittest
from s7_gate import parse_maps, inspect_legacy_source, analyze
class S7Tests(unittest.TestCase):
 def test_map_parsing(self):
  rows=parse_maps('f3961000-f3962000 r-xp 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so')
  self.assertEqual(rows[0]['start'],0xf3961000)
  self.assertEqual(rows[0]['path'],'/apex/com.android.runtime/lib/bionic/libdl.so')
 def test_legacy_rejection(self):
  src='scratch=(original.r[13]+256u)&~3u;\nrc=sc4(114,pid,(int)&st,0,0);\nmodified.r[14]=0;\nint v=sc4(26,2,pid,scratch+4*i,0);'
  self.assertEqual(len(inspect_legacy_source(src)),4)
 def test_reject_wrong_uid(self):
  faults,_=analyze('', 'Uid:\t2000\nTracerPid:\t0\nThreads:\t1\n', 'droid.bluetooth', ['1'], '1',1)
  self.assertIn('Bluetooth UID mismatch',faults)
 def test_reject_changed_pid(self):
  faults,_=analyze('', 'Uid:\t1002\nTracerPid:\t0\nThreads:\t1\n','droid.bluetooth',['1'],'2',1)
  self.assertIn('PID changed during snapshot',faults)
if __name__=='__main__':unittest.main()
