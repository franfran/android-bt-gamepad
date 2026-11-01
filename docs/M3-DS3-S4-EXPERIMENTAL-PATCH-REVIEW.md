# Experimental pinned-BSP BTA admission guard (NOT DEPLOYABLE)

Pinned public source: BPI-H618-Android12 commit `250eabfc529518b7f26432663ed0a867ab2f625d`, `system/bt` tree `d6f07310f73694977b301eac63d67b219ca20625`.

Patch: `experiments/m3-source-first/bta_w4_guard_EXPERIMENTAL.patch`.

This is a narrowly scoped **offline experiment** in `system/bt/bta/hh/bta_hh_act.cc`. It rejects a new handshake-bearing Classic HID operation before `HID_HostWriteDev` whenever the existing `p_cb->w4_evt` is already set. It frees the incoming report buffer and routes a generic failure to the existing application callback. It does not alter global L2CAP security, Java HID policy, or write a UHID reply.

**What it establishes:** a concrete compile-oriented insertion site for a pre-send admission guard. Fixture tests check diff syntax/applicability and confirm rejection semantics are present. They do NOT test full BSP compilation, actual BTA event state, ownership of all payloads, or kernel completion.

**Known unresolved correctness issues (deployment NO_GO):**
- This is **rejection**, not a proper serialization queue. A rejected UHID-origin SET still has no request-specific error reply and could time out in kernel.
- `w4_evt == 0` is an imperfect idle signal; a late handshake may appear after it is cleared. The patch adds no token, generation, or proof of remote completion.
- Per-handle callbacks for HID SET, GET and protocol may need distinct event-specific error data, and `cbdata` only carries generic status; real ABI, BTA cleanup and ownership must be inspected before enabling.
- LE HID branch and command producers other than this BTA path are not covered. Existing hardware behavior must be preserved.
- No offline ARM32 Soong compilation or OEM ELF ABI comparison has been performed.

**Evidence:** `test_bta_patch_fixture.py` checks `git apply --check` against a minimal exact-context synthetic file; successful CI is only fixture coverage, not verified applicability to an entire BSP checkout. Do not apply to a live M3 or distribute as a working replacement library.

**Next:** introduce a transaction-aware native design that rejects/queues with explicit owner identification and delivers correlated negative UHID completion on local failures, without assuming a handshake is unique. Independently solve per-DS3 native auth and OEM Java bond policy.
