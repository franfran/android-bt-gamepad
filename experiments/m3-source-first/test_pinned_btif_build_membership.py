#!/usr/bin/env python3
"""Verify actual modified BTIF files are built into pinned Android12 libbluetooth."""
import hashlib
import urllib.request
REV="250eabfc529518b7f26432663ed0a867ab2f625d"
FILES=("system/bt/main/Android.bp","system/bt/btif/Android.bp","system/bt/btif/include/btif_hh.h")
def fetch(path):
    with urllib.request.urlopen(f"https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/{REV}/{path}",timeout=30) as resp:
        raw=resp.read()
    return raw.decode(),hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def main():
    main_bp, main_hash=fetch(FILES[0])
    btif_bp, btif_hash=fetch(FILES[1])
    header,header_hash=fetch(FILES[2])
    module=btif_bp.split('name: "libbtif"',1)[1].split("\n}",1)[0]
    assert 'cc_library_static {' in btif_bp.split('name: "libbtif"',1)[0][-70:]
    for path in ('"co/bta_hh_co.cc"','"src/btif_hh.cc"'):
        assert module.count(path)==1, (path, "not a unique libbtif source")
    assert 'name: "libbluetooth"' in main_bp
    shared=main_bp.split('name: "libbluetooth"',1)[1].split("\n}",1)[0]
    assert '"libbtif"' in shared.split("whole_static_libs:",1)[1]
    assert 'extern void btif_hh_setreport(' in header
    assert 'extern bool btif_hh_try_enqueue_setreport(' not in header
    print("PASS actual Soong path: BTIF source files -> libbtif static -> libbluetooth shared")
    print(f"PINNED: main={main_hash} btif={btif_hash} public-header={header_hash}")
    print("NO Android/Soong compilation, no deployable binary or ABI proof")
if __name__=="__main__":main()
