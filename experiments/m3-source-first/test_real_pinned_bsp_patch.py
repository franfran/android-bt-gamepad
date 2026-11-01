#!/usr/bin/env python3
"""Check experimental patch against the REAL SHA-pinned upstream file, offline from M3.

Network fetch is for CI public source only. No device, no OEM artifacts.
"""
import hashlib
import pathlib
import subprocess
import tempfile
import urllib.request

COMMIT = "250eabfc529518b7f26432663ed0a867ab2f625d"
BLOB = "bc092b68c12502d2f73a7dbab65426ab05fd28c1"
PATH = "system/bt/bta/hh/bta_hh_act.cc"
ROOT = pathlib.Path(__file__).resolve().parents[2]
PATCH = ROOT / "experiments/m3-source-first/bta_w4_guard_EXPERIMENTAL.patch"

def main():
    url = f"https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/{COMMIT}/{PATH}"
    with urllib.request.urlopen(url, timeout=25) as response:
        source = response.read()
    # Git object identity is not the ordinary SHA1 of file contents.
    git_blob = hashlib.sha1(b"blob " + str(len(source)).encode() + b"\\0" + source).hexdigest()
    if git_blob != BLOB:
        raise RuntimeError(f"Upstream blob mismatch: {git_blob}")
    with tempfile.TemporaryDirectory() as tmp:
        target = pathlib.Path(tmp) / PATH
        target.parent.mkdir(parents=True)
        target.write_bytes(source)
        subprocess.run(["git", "apply", "--check", str(PATCH)], cwd=tmp, check=True)
        subprocess.run(["git", "apply", str(PATCH)], cwd=tmp, check=True)
        result = target.read_text()
        assert "expects_handshake && p_cb->w4_evt != 0" in result
        assert "HID_HostWriteDev(p_cb->hid_handle" in result
    print(f"PASS pinned blob {BLOB}; experimental patch applied against real upstream source")
    print("NOT a compile, transaction-safety, ABI, or deployment PASS")

if __name__ == "__main__":
    main()
