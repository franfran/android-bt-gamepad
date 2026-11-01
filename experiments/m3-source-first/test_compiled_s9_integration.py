#!/usr/bin/env python3
"""Compile/link actual S9 transformed BTIF helper, declaration and UHID SET call site with mocks.

Host source extraction; NOT an Android/Soong/ARM32 build or a live kernel reply.
"""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import urllib.request

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("s9",HERE/"test_integrated_btif_allocation_source.py")
s9=importlib.util.module_from_spec(spec);spec.loader.exec_module(s9)
def main():
    sources={}
    for f in s9.FILES:
        url=f"https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/{s9.REV}/{s9.BASE}{f}"
        with urllib.request.urlopen(url,timeout=30) as response: sources[f]=response.read().decode()
    modified=s9.transform(dict(sources))
    btif=modified["btif/src/btif_hh.cc"]
    start=btif.index("bool btif_hh_try_enqueue_setreport(")
    stop=btif.index("\n}",btif.index("void btif_hh_setreport(",start))+2
    methods=btif[start:stop]
    header=modified["btif/include/btif_hh.h"]
    assert "extern bool btif_hh_try_enqueue_setreport(" in header
    co=modified["btif/co/bta_hh_co.cc"]
    a=co.index("const uint32_t kernel_set_request_id")
    end=co.index("// A true value means BTA enqueue attempted",a)
    ingress=co[a:end]
    harness=r"""
#include <cstdint>
#include <cstddef>
using bthh_report_type_t=int;
struct BT_HDR {};
struct btif_hh_device_t { int dev_handle; };
constexpr int UHID_FEATURE_REPORT=1, UHID_OUTPUT_REPORT=2, UHID_INPUT_REPORT=3;
constexpr int BTHH_FEATURE_REPORT=10,BTHH_OUTPUT_REPORT=20,BTHH_INPUT_REPORT=30;
struct SetReport { uint32_t id; uint8_t rtype; uint16_t size; uint8_t data[4]; };
struct Event { struct { SetReport set_report; } u; };
bool fail_alloc=false; int sends=0; BT_HDR buffer;
BT_HDR* create_pbuf(uint16_t,uint8_t*) { return fail_alloc?nullptr:&buffer; }
void BTA_HhSetReport(int,int,BT_HDR*) { ++sends; }
#define APPL_TRACE_ERROR(...) ((void)0)
""" + methods + r"""
bool kernel_ingress(btif_hh_device_t* p_dev, Event ev) {
""" + ingress + r"""
(void)kernel_set_request_id; // host logging macro has no side effects
return queued_locally;
}
int main() {
  btif_hh_device_t dev{8};
  Event e{{{0xffffffffu,UHID_FEATURE_REPORT,2,{0,1,0,0}}}};
  fail_alloc=true;
  if(kernel_ingress(&dev,e) || sends!=0) return 1;
  fail_alloc=false;
  if(!kernel_ingress(&dev,e) || sends!=1) return 2;
  e.u.set_report.rtype=UHID_INPUT_REPORT;
  if(!kernel_ingress(&dev,e) || sends!=2) return 3;
  e.u.set_report.rtype=255;
  if(kernel_ingress(&dev,e) || sends!=2) return 4;
  btif_hh_setreport(&dev,BTHH_FEATURE_REPORT,2,e.u.set_report.data);
  return sends==3 ? 0 : 5;
}
"""
    with tempfile.TemporaryDirectory() as t:
        root=Path(t);(root/"test.cc").write_text(harness)
        for compiler in ("c++","clang++"):
            exe=root/("test-"+compiler)
            subprocess.run([compiler,"-std=c++17","-Wall","-Wextra","-Werror","-pedantic",
                            str(root/"test.cc"),"-o",str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
            print("PASS compiled S9 transformed helper + ingress:",compiler)
    print("NOT a complete BSP or ARM32 Soong build")
if __name__=="__main__":main()
