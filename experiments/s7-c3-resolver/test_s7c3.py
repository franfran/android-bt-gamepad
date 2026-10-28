import unittest,struct
import s7c3
class Tests(unittest.TestCase):
 def test_parse_exact(self):
  r=s7c3.maps_parse('ead30000-ead31000 r--p 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so')
  self.assertEqual(r[0]['start'],0xead30000)
 def test_thumb(self):
  rows=s7c3.maps_parse('ead30000-ead31000 r--p 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so\nead31000-ead32000 r-xp 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so')
  loads=[dict(offset=0,vaddr=0,memsz=0x848,flags=4,align=4096),dict(offset=0x848,vaddr=0x1848,memsz=0x218,flags=5,align=4096)]
  result=s7c3.resolve(rows,loads,0x1851)
  self.assertEqual(result['thumb_function_pointer'],'0xead31851')
  self.assertEqual(result['file_offset'],'0x850')
 def test_bionic_triplicate_zero_offset(self):
  raw='\n'.join([
   'ead30000-ead31000 r--p 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so',
   'ead31000-ead32000 r-xp 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so',
   'ead32000-ead33000 r--p 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so'])
  loads=[dict(offset=0,vaddr=0,memsz=0x848,flags=4,align=4096),dict(offset=0x848,vaddr=0x1848,memsz=0x218,flags=5,align=4096),dict(offset=0xa60,vaddr=0x2a60,memsz=0xcc,flags=6,align=4096)]
  for value,expected in ((0x1851,'0xead31851'),(0x1897,'0xead31897')):
   r=s7c3.resolve(s7c3.maps_parse(raw),loads,value)
   self.assertEqual(r['thumb_function_pointer'],expected)
 def test_unmapped_nonexec_load_is_not_symbol_blocker(self):
  raw='\n'.join([
   'ead30000-ead31000 r--p 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so',
   'ead31000-ead32000 r-xp 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so',
   'ead32000-ead33000 r--p 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so'])
  loads=[dict(offset=0,vaddr=0,memsz=0x848,flags=4,align=4096),
         dict(offset=0x848,vaddr=0x1848,memsz=0x218,flags=5,align=4096),
         dict(offset=0xa60,vaddr=0x2a60,memsz=0xcc,flags=6,align=4096),
         dict(offset=0x1000,vaddr=0x4000,memsz=0x1000,flags=6,align=4096)]
  result=s7c3.resolve(s7c3.maps_parse(raw),loads,0x1851)
  self.assertEqual(result['thumb_function_pointer'],'0xead31851')
 def test_reject_symbol_in_gap(self):
  raw='\n'.join([
   'ead30000-ead31000 r--p 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so',
   'ead31000-ead32000 r-xp 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so'])
  loads=[dict(offset=0,vaddr=0,memsz=0x848,flags=4,align=4096),
         dict(offset=0x848,vaddr=0x1848,memsz=0x218,flags=5,align=4096)]
  with self.assertRaises(ValueError):s7c3.resolve(s7c3.maps_parse(raw),loads,0x2301)
 def test_reject_missing_header_mapping(self):
  raw='ead31000-ead32000 r-xp 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so'
  loads=[dict(offset=0,vaddr=0,memsz=0x848,flags=4,align=4096)]
  with self.assertRaises(ValueError):s7c3.resolve(s7c3.maps_parse(raw),loads,0x1851)
 def test_reject_nonexecutable(self):
  rows=s7c3.maps_parse('ead30000-ead31000 r--p 00000000 fd:00 428 /apex/com.android.runtime/lib/bionic/libdl.so')
  with self.assertRaises(ValueError):s7c3.resolve(rows,[dict(offset=0,vaddr=0,memsz=0x2000,flags=5,align=4096)],0x1851)
 def test_reject_wrong_uid(self):
  targets,issues=s7c3.evaluate(675,'droid.bluetooth','Uid:\t0\nTracerPid:\t0\n',[],[],{},'675')
  self.assertIn('unexpected UID',issues)
if __name__=='__main__':unittest.main()
