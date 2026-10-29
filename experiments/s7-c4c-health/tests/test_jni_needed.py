import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import subprocess

path=Path(__file__).resolve().parents[1]/"read-only-jni-needed.py"
spec=importlib.util.spec_from_file_location("needed",path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def elf(names=("libc.so","liblog.so")):
    buf=bytearray(1024)
    buf[:7]=b"\x7fELF\x01\x01\x01"
    struct.pack_into("<HHIIIIIHHHHHH",buf,16,3,40,1,0,52,0,0,52,32,2,0,0,0)
    # Entire image mapped from virtual address 0x1000
    struct.pack_into("<IIIIIIII",buf,52,1,0,0x1000,0,1024,1024,5,4096)
    struct.pack_into("<IIIIIIII",buf,84,2,256,0x1100,0,128,128,4,4)
    strings=b"\x00"; indices=[]
    for name in names:
        indices.append(len(strings))
        strings+=name.encode()+b"\x00"
    buf[512:512+len(strings)]=strings
    entries=[(5,0x1200),(10,len(strings))]+[(1,i) for i in indices]+[(0,0)]
    for n,pair in enumerate(entries):
        struct.pack_into("<II",buf,256+n*8,*pair)
    return bytes(buf)

class Tests(unittest.TestCase):
    def test_needed_sorted_and_exact(self):
        self.assertEqual(mod.needed(elf()),["libc.so","liblog.so"])

    def test_elf_malformed_rejected(self):
        with self.assertRaises(ValueError):
            mod.needed(b"not an ELF")
        with self.assertRaises(ValueError):
            mod.needed(elf(("bad/library.so",)))

    def test_read_only_uses_fixed_path(self):
        p=subprocess.CompletedProcess([],0,elf(),b"")
        with patch.object(mod.subprocess,"run",return_value=p) as run:
            result=mod.inspect("serial")
        self.assertEqual(result["needed_libraries"],["libc.so","liblog.so"])
        self.assertEqual(run.call_args.args[0][-1],"cat /system/lib/libbluetooth_jni.so")
        self.assertEqual(result["caller_linker_namespace"],"UNVERIFIED")
        self.assertEqual(result["decision"],"NO_GO")

if __name__=="__main__":
    unittest.main()
