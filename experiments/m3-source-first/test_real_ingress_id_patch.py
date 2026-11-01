#!/usr/bin/env python3
"""Validate that an offline ID-ingress patch applies to the pinned public BSP blob."""
import hashlib
import pathlib
import subprocess
import tempfile
import urllib.request

COMMIT = "250eabfc529518b7f26432663ed0a867ab2f625d"
PATH = "system/bt/btif/co/bta_hh_co.cc"
BLOB = "c5aba4425d272dc963b6f60567d7b79fb0c18f75"
PATCH = pathlib.Path(__file__).with_name("uhid_ingress_id_EXPERIMENTAL.patch")

def main():
    url = f"https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/{COMMIT}/{PATH}"
    with urllib.request.urlopen(url, timeout=25) as resp:
        raw = resp.read()
    identity = hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest()
    if identity != BLOB:
        raise RuntimeError(f"Pinned source changed: {identity}")
    with tempfile.TemporaryDirectory() as temporary:
        target = pathlib.Path(temporary) / PATH
        target.parent.mkdir(parents=True)
        target.write_bytes(raw)
        subprocess.run(["git", "apply", "--check", str(PATCH)], cwd=temporary, check=True)
        subprocess.run(["git", "apply", str(PATCH)], cwd=temporary, check=True)
        changed = target.read_text()
        assert "const uint32_t uhid_request_id = ev.u.set_report.id;" in changed
        assert "(void)uhid_request_id;" in changed
    print("PASS: pinned BSP ingress patch applies; identity is LOCAL-ONLY, no reply writer")

if __name__ == "__main__":
    main()
