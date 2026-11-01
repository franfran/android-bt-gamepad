# S7 source-local kernel origin boundary

Public source pin: BPI H618 Android12 `250eabfc529518b7f26432663ed0a867ab2f625d`; `btif/co/bta_hh_co.cc` blob `c5aba4425d272dc963b6f60567d7b79fb0c18f75`.

`experiments/m3-source-first/uhid_origin_boundary_EXPERIMENTAL.patch` captures `ev.u.set_report.id` and `ev.u.set_report.rtype` at the real UHID SET ingress, explicitly distinguishing kernel-request provenance from the `UHID_OUTPUT` Feature producer. The values remain local and unused, intentionally preserving existing BSP behavior. `test_real_origin_boundary_patch.py` validates exact upstream blob identity and applies diff in an ephemeral source tree.

**Not a native integration:** These variables are intentionally discarded, do not enter `btif_hh_setreport`, are not retained through BTA dispatch, cannot associate a handshake with request ID, and do not yield any `UHID_SET_REPORT_REPLY`. This experiment is not safe or useful for deployment. It provides a verified modification anchor only.

Next real integration requires a source-aware private request owner visible to BTIF allocation failure and BTA asynchronous completion, without global HID regressions; callback generation must be proven before any kernel reply. Native auth 0x22, Java bond policy, Soong ARM32 and OEM ABI remain independent open gates. M3 untouched, PR #51 Draft, PR #50 unmerged.
