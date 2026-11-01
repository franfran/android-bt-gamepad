#!/usr/bin/env python3
"""Fail-closed static deployment gate for *experimental* BTA patch.

A PASS means unsafe candidate was correctly rejected, never deployment approval.
"""
from pathlib import Path
import sys

PATCH = Path(__file__).with_name("bta_w4_guard_EXPERIMENTAL.patch")
def audit(text):
    issues = []
    if "if (expects_handshake && p_cb->w4_evt != 0)" in text:
        issues.append("global_classic_hid_guard_not_ds3_scoped")
    if '(*bta_hh_cb.p_cback)(event, (tBTA_HH*)&cbdata);' in text and "UHID_SET_REPORT_REPLY" not in text:
        issues.append("kernel_set_rejection_lacks_correlated_uhid_error")
    if "request_id" not in text and "set_report.id" not in text:
        issues.append("missing_uhid_transaction_identity")
    if "generation" not in text:
        issues.append("no_disconnect_generation_isolation")
    return issues

def main():
    issues = audit(PATCH.read_text())
    expected = {"global_classic_hid_guard_not_ds3_scoped",
                "kernel_set_rejection_lacks_correlated_uhid_error",
                "missing_uhid_transaction_identity",
                "no_disconnect_generation_isolation"}
    if set(issues) != expected:
        print("FAIL: experimental patch safety classification changed; manual review required:", issues)
        return 1
    print("PASS: candidate correctly classified DEPLOYMENT NO_GO:", ", ".join(issues))
    return 0

if __name__ == "__main__":
    sys.exit(main())
