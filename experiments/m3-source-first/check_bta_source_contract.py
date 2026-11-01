#!/usr/bin/env python3
"""Offline contract audit for pinned H618 Fluoride control path.
A passing source audit documents existing hazards; it is NOT a patch approval.
"""
import argparse
from pathlib import Path
import sys

FILES = {
 "system/bt/bta/hh/bta_hh_api.cc": (
    "BTA_HH_API_WRITE_DEV_EVT", "bta_sys_sendmsg(p_buf)", "HID_TRANS_SET_REPORT"),
 "system/bt/stack/hid/hidh_api.cc": (
    "HID_HostWriteDev(", "hidh_conn_snd_data(", "osi_free(pbuf)"),
 "system/bt/bta/hh/bta_hh_act.cc": (
    "HID_HostWriteDev(", "p_cb->w4_evt = event", "bta_hh_co_set_rpt_rsp("),
 "system/bt/stack/hid/hidh_conn.cc": (
    "HID_HDEV_EVT_HANDSHAKE", "HID_TRANS_HANDSHAKE"),
 "system/bt/btif/co/bta_hh_co.cc": (
    "UHID_SET_REPORT", "UHID_SET_REPORT_REPLY not supported", "ev.u.feature.id"),
}

def audit(root: Path) -> dict[str, bool]:
    outcome = {}
    for name, phrases in FILES.items():
        try:
            contents = (root / name).read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            outcome[name] = False
            continue
        outcome[name] = all(phrase in contents for phrase in phrases)
    return outcome

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bsp", type=Path, required=True)
    a = p.parse_args()
    results = audit(a.bsp)
    for name, ok in results.items():
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    print("Only marker presence verified; callgraph, token safety and ABI remain UNVERIFIED.")
    return 0 if all(results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
