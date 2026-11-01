#!/usr/bin/env python3
"""Compile extracted, patched BTIF functions with strict host C++ stubs.

Does NOT compile the Android BSP or establish ARM32/ABI compatibility.
"""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import urllib.request

COMMIT="250eabfc529518b7f26432663ed0a867ab2f625d"
PATH="system/bt/btif/src/btif_hh.cc"
BLOB="9e5db0c1af234881048732d8bc4816f23b2a33ba"
PATCH=Path(__file__).with_name("btif_allocation_boundary_EXPERIMENTAL.patch")
PREFACE=r"""
#include <cstdint>
#include <cstddef>
using bthh_report_type_t = int;
struct BT_HDR {};
struct btif_hh_device_t { int dev_handle; };
static bool force_fail = false;
static int sends = 0;
static BT_HDR buffer;
BT_HDR* create_pbuf(uint16_t, uint8_t*) { return force_fail ? nullptr : &buffer; }
void BTA_HhSetReport(int, int, BT_HDR*) { ++sends; }
#define APPL_TRACE_ERROR(...) ((void)0)
"""

def main():
    url=f"https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/{COMMIT}/{PATH}"
    with urllib.request.urlopen(url,timeout=30) as response: raw=response.read()
    digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()
    if digest != BLOB: raise RuntimeError("wrong source blob: "+digest)
    with tempfile.TemporaryDirectory() as tmp:
        dest=Path(tmp)/PATH
        dest.parent.mkdir(parents=True)
        dest.write_bytes(raw)
        subprocess.run(["git","apply","--check",str(PATCH)],cwd=tmp,check=True)
        subprocess.run(["git","apply",str(PATCH)],cwd=tmp,check=True)
        patched=dest.read_text()
        start=patched.index("static bool btif_hh_enqueue_setreport(")
        end=patched.index("\n}",patched.index("void btif_hh_setreport(",start))+2
        extracted=patched[start:end]
        harness=PREFACE+extracted+r"""
int main() {
  btif_hh_device_t dev{7};
  uint8_t report[2] = {0,1};
  force_fail=true;
  if(btif_hh_enqueue_setreport(&dev,1,2,report) || sends!=0) return 1;
  force_fail=false;
  if(!btif_hh_enqueue_setreport(&dev,1,2,report) || sends!=1) return 2;
  btif_hh_setreport(&dev,1,2,report);
  return sends==2 ? 0 : 3;
}
"""
        source=Path(tmp)/"extract.cc"
        source.write_text(harness)
        for compiler in ("c++","clang++"):
            executable=Path(tmp)/("test-"+compiler)
            subprocess.run([compiler,"-std=c++17","-Wall","-Wextra","-Werror","-pedantic",str(source),"-o",str(executable)],check=True)
            subprocess.run([str(executable)],check=True)
            print("PASS source-extracted BTIF function host compile/run:",compiler)
    print("NOT a full BSP or ARM32 Soong build; unrelated Android headers mocked.")

if __name__=="__main__":main()
