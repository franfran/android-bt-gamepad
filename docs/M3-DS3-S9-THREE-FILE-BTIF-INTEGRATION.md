# S9 three-file BTIF ingress / allocation-result integration

Pinned BPI H618 Android12 public BSP commit `250eabfc529518b7f26432663ed0a867ab2f625d`.

Source generator/test: `experiments/m3-source-first/test_integrated_btif_allocation_source.py`. It downloads and validates three pinned files, builds an **actual integrated patch** across `btif/co/bta_hh_co.cc`, `btif/src/btif_hh.cc`, and `btif/include/btif_hh.h`, then verifies `git apply --check`, applies the diff to a temporary public BSP fragment tree and compares results. Run `python3 experiments/m3-source-first/test_integrated_btif_allocation_source.py --print-patch` to inspect the generated unified diff.

The private `bool btif_hh_try_enqueue_setreport` is declared in the BTIF header and defined in the source; existing public `void btif_hh_setreport` is preserved. The kernel `UHID_SET_REPORT` ingress now **consumes the local bool result** for every report type and logs the original kernel request ID if the buffer cannot be queued. The separate `UHID_OUTPUT` path remains unchanged.

**Not implemented:** this is local diagnostic behavior only; an unsuccessful request still has no correlated kernel error completion, and successful BTA enqueue still cannot be attributed to a unique remote handshake. The patch does NOT issue a `UHID_SET_REPORT_REPLY`. The test validates exact pinned-source transformation, **not** full C++ compile or ARM32 Soong build, OEM ABI or runtime safety.

**CI note:** initial test failed because its comment contained the token `UHID_SET_REPORT_REPLY`; the static no-reply assertion was narrowed to an actual event assignment and rerun successfully. Never infer deployment readiness from this check.

No M3 operations, library replacement, flashing, security bypass or merge. PR #51 Draft; PR #50 independent and unmerged. Native auth 0x22 and Java bond policy unresolved.
