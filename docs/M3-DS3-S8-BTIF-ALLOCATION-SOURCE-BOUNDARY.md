# S8 BTIF local-allocation boundary — real pinned-source patch

Pinned public H618 Android12 BSP: `250eabfc529518b7f26432663ed0a867ab2f625d`; `btif/src/btif_hh.cc` Git blob `9e5db0c1af234881048732d8bc4816f23b2a33ba`.

`experiments/m3-source-first/btif_allocation_boundary_EXPERIMENTAL.patch` refactors the `btif_hh_setreport` implementation into an internal `static bool btif_hh_enqueue_setreport` (which reports *only* create_pbuf allocation success / BTA enqueue attempt) plus the existing void wrapper. This changes actual source behavior only insofar as the helper returns a value; it deliberately preserves the public wrapper signature and report flow. No kernel request ID reaches the helper, no caller consumes the result, and no UHID reply is created. A success result must not be treated as transport success or remote acknowledgement.

`test_real_btif_allocation_patch.py` checks Git blob identity and `git apply` against that exact upstream file in a temporary tree.

**Remaining deployment blockers:** no kernel-origin request-specific consumption of the helper result; no safe BTA callback identity; no per-DS3 isolation; no real Android12 ARM32 Soong build or OEM binary ABI checks. Patch is an **OFFLINE RESEARCH PROTOTYPE, NOT DEPLOYABLE**. Do not apply to M3, flash, restart Bluetooth or replace libbluetooth.so. PR #51 remains Draft; PR #50 unmerged.
