#!/usr/bin/env python3
"""Build and test OFFLINE integrated 3-file BTIF allocation-result prototype.

Downloads immutable public BSP sources, never modifies an Android device.
"""
import difflib
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.request

REV = "250eabfc529518b7f26432663ed0a867ab2f625d"
BASE = "system/bt/"
FILES = {
    "btif/src/btif_hh.cc": "9e5db0c1af234881048732d8bc4816f23b2a33ba",
    "btif/co/bta_hh_co.cc": "c5aba4425d272dc963b6f60567d7b79fb0c18f75",
    "btif/include/btif_hh.h": None,
}

def once(text, before, after, label):
    if text.count(before) != 1:
        raise AssertionError(f"{label}: expected one anchor, got {text.count(before)}")
    return text.replace(before, after, 1)

def transform(files):
    btif = files["btif/src/btif_hh.cc"]
    orig = '''void btif_hh_setreport(btif_hh_device_t* p_dev, bthh_report_type_t r_type,
                       uint16_t size, uint8_t* report) {
  BT_HDR* p_buf = create_pbuf(size, report);
  if (p_buf == NULL) {
    APPL_TRACE_ERROR("%s: Error, failed to allocate RPT buffer, size = %d",
                     __func__, size);
    return;
  }
  BTA_HhSetReport(p_dev->dev_handle, r_type, p_buf);
}'''
    repl = '''// RetroBox OFFLINE EXPERIMENT: returns only local allocation acceptance.
bool btif_hh_try_enqueue_setreport(btif_hh_device_t* p_dev, bthh_report_type_t r_type,
                                   uint16_t size, uint8_t* report) {
  BT_HDR* p_buf = create_pbuf(size, report);
  if (p_buf == NULL) {
    APPL_TRACE_ERROR("%s: Error, failed to allocate RPT buffer, size = %d",
                     __func__, size);
    return false;
  }
  BTA_HhSetReport(p_dev->dev_handle, r_type, p_buf);
  return true;
}
void btif_hh_setreport(btif_hh_device_t* p_dev, bthh_report_type_t r_type,
                       uint16_t size, uint8_t* report) {
  (void)btif_hh_try_enqueue_setreport(p_dev, r_type, size, report);
}'''
    files["btif/src/btif_hh.cc"] = once(btif, orig, repl, "BTIF helper")
    head = files["btif/include/btif_hh.h"]
    anchor = '''extern void btif_hh_setreport(btif_hh_device_t* p_dev,
                              bthh_report_type_t r_type, uint16_t size,
                              uint8_t* report);'''
    added = '''// Local buffer allocation/enqueue only; not a remote HID acknowledgement.
extern bool btif_hh_try_enqueue_setreport(btif_hh_device_t* p_dev,
                                          bthh_report_type_t r_type,
                                          uint16_t size, uint8_t* report);
''' + anchor
    files["btif/include/btif_hh.h"] = once(head, anchor, added, "header declaration")
    co = files["btif/co/bta_hh_co.cc"]
    before = '''        if (ev.u.set_report.rtype == UHID_FEATURE_REPORT)
            btif_hh_setreport(p_dev, BTHH_FEATURE_REPORT,
                              ev.u.set_report.size, ev.u.set_report.data);
        else if (ev.u.set_report.rtype == UHID_OUTPUT_REPORT)
            btif_hh_setreport(p_dev, BTHH_OUTPUT_REPORT,
                              ev.u.set_report.size, ev.u.set_report.data);
        else if(ev.u.set_report.rtype == UHID_INPUT_REPORT)
            btif_hh_setreport(p_dev, BTHH_INPUT_REPORT,
                              ev.u.set_report.size, ev.u.set_report.data);
        else
            APPL_TRACE_ERROR("%s:UHID_SET_REPORT: Invalid Report type = %d"
                          , __func__, ev.u.set_report.rtype);'''
    after = '''        // Preserve provenance at UHID ingress; DO NOT fabricate a kernel ACK.
        const uint32_t kernel_set_request_id = ev.u.set_report.id;
        bool queued_locally = false;
        if (ev.u.set_report.rtype == UHID_FEATURE_REPORT)
            queued_locally = btif_hh_try_enqueue_setreport(
                p_dev, BTHH_FEATURE_REPORT, ev.u.set_report.size, ev.u.set_report.data);
        else if (ev.u.set_report.rtype == UHID_OUTPUT_REPORT)
            queued_locally = btif_hh_try_enqueue_setreport(
                p_dev, BTHH_OUTPUT_REPORT, ev.u.set_report.size, ev.u.set_report.data);
        else if (ev.u.set_report.rtype == UHID_INPUT_REPORT)
            queued_locally = btif_hh_try_enqueue_setreport(
                p_dev, BTHH_INPUT_REPORT, ev.u.set_report.size, ev.u.set_report.data);
        else
            APPL_TRACE_ERROR("%s:UHID_SET_REPORT: Invalid Report type = %d"
                          , __func__, ev.u.set_report.rtype);
        if (!queued_locally)
            APPL_TRACE_ERROR("UHID_SET_REPORT not locally queued (id=%u)",
                             kernel_set_request_id);
        // A true value means BTA enqueue attempted; never issue UHID_SET_REPORT_REPLY here.'''
    files["btif/co/bta_hh_co.cc"] = once(co, before, after, "kernel SET case")
    return files

def main():
    sources={}
    for relative, expected in FILES.items():
        url=f"https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/{REV}/{BASE}{relative}"
        with urllib.request.urlopen(url, timeout=30) as response: raw=response.read()
        digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()
        if expected and digest!=expected: raise AssertionError(f"blob mismatch: {relative}: {digest}")
        sources[relative]=raw.decode("utf-8")
    patched=transform(dict(sources))
    diff=""
    for relative in FILES:
        old=sources[relative].splitlines(keepends=True)
        new=patched[relative].splitlines(keepends=True)
        diff+="".join(difflib.unified_diff(old,new,fromfile="a/"+BASE+relative,tofile="b/"+BASE+relative))
    assert "ev.type = UHID_SET_REPORT_REPLY" not in (patched["btif/co/bta_hh_co.cc"].split("const uint32_t kernel_set_request_id",1)[1].split("break;",1)[0])
    assert "btif_hh_try_enqueue_setreport(" in patched["btif/co/bta_hh_co.cc"]
    assert "btif_hh_setreport(p_dev, BTHH_FEATURE_REPORT, ev.u.output.size," in patched["btif/co/bta_hh_co.cc"]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)
        for relative, data in sources.items():
            out=root/(BASE+relative)
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_text(data)
        patch=root/"integration.patch";patch.write_text(diff)
        subprocess.run(["git","apply","--check",str(patch)],cwd=root,check=True)
        subprocess.run(["git","apply",str(patch)],cwd=root,check=True)
        for relative in FILES:
            assert (root/(BASE+relative)).read_text()==patched[relative]
    if "--print-patch" in sys.argv: print(diff, end="")
    print("PASS: actual pinned 3-file BTIF ingress/local allocation integration (offline)")
    print("NO correlated UHID reply; no native completion identity; NOT an ARM32 build")

if __name__=="__main__": main()
