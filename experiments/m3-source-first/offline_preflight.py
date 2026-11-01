#!/usr/bin/env python3
"""Offline-only source provenance and ARM32 ELF preflight for M3 DS3.

Never connects to an Android device. Stdlib only; requires Git/readelf installed.
This is a preflight, not certification of OEM ABI or deployment safety.
"""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys

PINNED_COMMIT = "250eabfc529518b7f26432663ed0a867ab2f625d"
PINNED_BT_TREE = "d6f07310f73694977b301eac63d67b219ca20625"
ORIGINAL_SHA256 = "4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85"
REQUIRED = {
    "system/bt/btif/co/bta_hh_co.cc": (
        "UHID_SET_REPORT",
        "ev.u.feature.id",
        "UHID_SET_REPORT_REPLY not supported",
        "bta_hh_co_set_rpt_rsp",
    ),
    "system/bt/bta/hh/bta_hh_act.cc": (
        "BTA_HH_SET_RPT_EVT", "bta_hh_co_set_rpt_rsp", "p_cb->w4_evt = 0"
    ),
    "system/bt/stack/hid/hidh_conn.cc": (
        "L2CA_Register2", "BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT"
    ),
    "system/bt/main/Android.bp": ('name: "libbluetooth"', "cc_library_shared"),
}


def run(*command, cwd=None):
    return subprocess.check_output(command, cwd=cwd, text=True, stderr=subprocess.STDOUT).strip()


def source_check(root):
    checks = {}
    try:
        actual_commit = run("git", "rev-parse", "HEAD", cwd=root)
        actual_tree = run("git", "rev-parse", "HEAD:system/bt", cwd=root)
        checks["pinned_commit"] = actual_commit == PINNED_COMMIT
        checks["pinned_system_bt_tree"] = actual_tree == PINNED_BT_TREE
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        checks["git_metadata"] = False
        print("source metadata error:", exc)
        return checks
    for name, markers in REQUIRED.items():
        file = root / name
        try:
            data = file.read_text(encoding="utf-8")
            checks[f"markers:{name}"] = all(m in data for m in markers)
        except OSError:
            checks[f"markers:{name}"] = False
    return checks


def elf_check(path):
    """Reject non-ELF32 ARM before any ABI comparison."""
    checks = {}
    data = path.read_bytes()
    checks["ELF32"] = len(data) >= 20 and data[:5] == b"\\x7fELF\\x01"
    checks["little_endian"] = len(data) >= 20 and data[5] == 1
    checks["EM_ARM"] = len(data) >= 20 and int.from_bytes(data[18:20], "little") == 40
    try:
        dynamic = run("readelf", "-d", str(path))
        checks["DT_SONAME_libbluetooth"] = bool(re.search(r"\\(SONAME\\).*\\[libbluetooth\\.so\\]", dynamic))
        print(f"ELF {path} SHA256:", hashlib.sha256(data).hexdigest())
        print("DT_NEEDED:", re.findall(r"\\(NEEDED\\).*\\[([^\\]]+)\\]", dynamic))
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        checks["readelf_available"] = False
        print("readelf error:", exc)
    return checks


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bsp", type=Path, required=True, help="Checkout of pinned H618 BSP")
    ap.add_argument("--built-elf", type=Path, help="Optional offline ARM32 build artifact")
    ap.add_argument("--original-elf", type=Path, help="Optional PRIVATE OEM ELF; never commit")
    args = ap.parse_args()
    checks = source_check(args.bsp.resolve())
    if args.built_elf:
        checks.update({f"built:{k}": v for k, v in elf_check(args.built_elf.resolve()).items()})
    if args.original_elf:
        path = args.original_elf.resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        checks["original_sha256"] = digest == ORIGINAL_SHA256
        checks.update({f"original:{k}": v for k, v in elf_check(path).items()})
    for key, value in checks.items():
        print(f"{'PASS' if value else 'FAIL'} {key}")
    print("NOTE: ABI parity, DS3 security policy and live execution remain UNVERIFIED.")
    return 0 if checks and all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
