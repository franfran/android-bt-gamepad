import unittest
from unittest.mock import patch
import stage

class StagingTests(unittest.TestCase):
 def test_hash(self):
  self.assertEqual(stage.sha256(b''),'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
 def test_path_constant(self):
  self.assertTrue(stage.REMOTE.startswith('/data/local/tmp/retrobox_s7c4_inert'))
  self.assertNotIn('/system/',stage.REMOTE)
 def test_no_injection_code(self):
  import inspect
  src=inspect.getsource(stage)
  self.assertNotIn('PTRACE_ATTACH',src)
  self.assertNotIn('PTRACE_SEIZE',src)
  self.assertNotIn('remote_dlopen',src)
 def test_cleanup_only_stage_files(self):
  with patch.object(stage,'shell',return_value='') as s, patch.object(stage.subprocess,'run'):
   result=stage.run('demo','cleanup')
   self.assertFalse(result['injection_authorized'])
   command=s.call_args.args[1]
   self.assertNotIn('/system',command)
   self.assertIn('retrobox_s7c4_inert',command)
 def test_stage_avoids_chmod(self):
  import inspect
  source=inspect.getsource(stage.run)
  self.assertNotIn("chmod 0755",source)
  self.assertNotIn("chmod 0644",source)
  self.assertIn("' && cp '",source)
  self.assertIn("UPLOAD",source)
if __name__=='__main__': unittest.main()
