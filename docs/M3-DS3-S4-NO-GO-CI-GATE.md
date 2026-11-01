# S4 deployment NO_GO classification gate

**Purpose:** Make the existing experimental BTA admission-guard patch's deficiencies machine-visible in CI, without mistaking a green CI check for runtime safety.

Run `python3 experiments/m3-source-first/check_experimental_patch_no_go.py`. It inspects `bta_w4_guard_EXPERIMENTAL.patch`, expects four exact diagnostic classifications, and exits nonzero if those markers change unexpectedly. A passing check means **the unsafe experimental patch remains identified as NOT DEPLOYABLE**.

Expected diagnostics:
- `global_classic_hid_guard_not_ds3_scoped`: affects all Classic HID operations reaching this branch, not an authenticated sixpair-enrolled DS3.
- `kernel_set_rejection_lacks_correlated_uhid_error`: old application error callback cannot unblock the original UHID kernel SET request by ID.
- `missing_uhid_transaction_identity`: request ID is not transported through BTA/HID.
- `no_disconnect_generation_isolation`: no proven handling of stale handshakes after disconnect/reconnect.

**Limit:** This is a simple static marker audit of an experimental patch, NOT a semantic code verifier, and is deliberately not a criterion for approving a runtime fix. Changing the patch requires reviewed evidence, not merely editing expected strings. It is separate from the existing real pinned-BSP `git apply` verification.

Next actionable source task: create a fail-closed production-oriented design for kernel-error response ownership, including error path for BTA invalid handle, local dispatch failure, and remote handshake; investigate safe token propagation without ABI mismatches and protect non-DS3 controllers.

M3 remains untouched; PR #51 stays Draft; PR #50 is research archive and stays unmerged.
