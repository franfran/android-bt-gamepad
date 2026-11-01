#!/usr/bin/env python3
"""Validate local allocation-boundary patch against exact public upstream source."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import urllib.request

COMMIT="250eabfc529518b7f26432663ed0a867ab2f625d"
BLOB="9e5db0c1af234881048732d8bc4816f23b2a33ba"
PATH="system/bt/btif/src/btif_hh.cc"
PATCH=Path(__file__).with_name("btif_allocation_boundary_EXPERIMENTAL.patch")
def main():
    url=f"https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/{COMMIT}/{PATH}"
    with urllib.request.urlopen(url,timeout=25) as resp: content=resp.read()
    identity=hashlib.sha1(b"blob "+str(len(content)).encode()+bytes([0])+content).hexdigest()
    assert identity==BLOB,(identity,BLOB)
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/PATH
        path.parent.mkdir(parents=True)
        path.write_bytes(content)
        subprocess.run(["git","apply","--check",str(PATCH)],cwd=tmp,check=True)
        subprocess.run(["git","apply",str(PATCH)],cwd=tmp,check=True)
        patched=path.read_text()
        assert "static bool btif_hh_enqueue_setreport(" in patched
        assert "return false;" in patched.split("static bool btif_hh_enqueue_setreport(",1)[1].split("void btif_hh_setreport(",1)[0]
        assert "(void)btif_hh_enqueue_setreport(" in patched
    print("PASS: actual pinned BTIF allocation-boundary patch applicable")
    print("NOT proof of runtime behavior, BTA acknowledgement or ARM32 build")
if __name__=="__main__":main()
