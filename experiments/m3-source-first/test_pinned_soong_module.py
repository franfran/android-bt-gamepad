#!/usr/bin/env python3
"""Audit pinned Soong libbluetooth build graph without pretending to build Android."""
import hashlib
import re
import urllib.request

REV="250eabfc529518b7f26432663ed0a867ab2f625d"
PATH="system/bt/main/Android.bp"
def main():
    with urllib.request.urlopen(f"https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/{REV}/{PATH}", timeout=30) as response:
        raw=response.read()
    sha=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    source=raw.decode()
    anchor='cc_library_shared {\n    name: "libbluetooth",'
    if source.count(anchor)!=1:
        raise AssertionError("Pinned Soong module declaration unavailable/ambiguous")
    module=source.split(anchor,1)[1].split("\ncc_",1)[0]
    required=['defaults: ["fluoride_defaults"]','"libbluetooth_headers"',
              '"libbte"','"libflatbuffers-cpp"','"android.hardware.bluetooth@1.0"']
    for marker in required:
        if marker not in module:
            raise AssertionError("Soong dependency declaration changed: "+marker)
    if 'srcs: [\n        ":LibBluetoothSources"' not in module:
        raise AssertionError("Expected generated source group missing")
    print("PASS: pinned libbluetooth Soong module structural audit; blob",sha)
    print("LIMIT: existence of module/dependencies, NOT resolved Android platform build")
    print("Missing platform checkout/out/soong, ARM32 product config, OEM ABI evidence")
if __name__=="__main__": main()
