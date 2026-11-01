#!/usr/bin/env python3
"""Fail-closed upstream source producer/alloc boundary assertion. No M3 access."""
import hashlib
import urllib.request

COMMIT = "250eabfc529518b7f26432663ed0a867ab2f625d"
FILES = {
    "btif/co/bta_hh_co.cc": ("c5aba4425d272dc963b6f60567d7b79fb0c18f75",
        ["case UHID_OUTPUT:", "case UHID_SET_REPORT:", "btif_hh_setreport(p_dev, BTHH_FEATURE_REPORT,"]),
    "btif/src/btif_hh.cc": (None,
        ["void btif_hh_setreport(", "BT_HDR* p_buf = create_pbuf(size, report);",
         "if (p_buf == NULL)", "BTA_HhSetReport(p_dev->dev_handle, r_type, p_buf);"]),
}

def run():
    sources = {}
    for path, (blob, checks) in FILES.items():
        url = f"https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/{COMMIT}/system/bt/{path}"
        with urllib.request.urlopen(url, timeout=25) as response:
            raw = response.read()
        identity = hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest()
        if blob and identity != blob:
            raise AssertionError(f"{path}: upstream identity mismatch {identity}")
        source = raw.decode("utf-8")
        for snippet in checks:
            if snippet not in source:
                raise AssertionError(f"{path}: missing {snippet}")
        sources[path] = source
        print(f"PASS pinned source marker audit: {path} blob={identity}")
    co = sources["btif/co/bta_hh_co.cc"]
    output = co.split("case UHID_OUTPUT:", 1)[1].split("case UHID_OUTPUT_EV:", 1)[0]
    kernel_set = co.split("case UHID_SET_REPORT:", 1)[1].split("default:", 1)[0]
    assert "btif_hh_setreport(" in output and "btif_hh_setreport(" in kernel_set
    btif = sources["btif/src/btif_hh.cc"]
    wrapper = btif.split("void btif_hh_setreport(", 1)[1].split("void btif_hh_senddata(", 1)[0]
    assert wrapper.index("if (p_buf == NULL)") < wrapper.index("BTA_HhSetReport(")
    assert "return;" in wrapper.split("if (p_buf == NULL)", 1)[1].split("BTA_HhSetReport(", 1)[0]
    print("PASS cross-producer same-wrapper + pre-BTA allocation exit")
    print("This is static source evidence, NOT behavioral/ARM32 validation")

if __name__ == "__main__":
    run()
