# I2/I6 — Request-bound BTM security callback reference, not CCB pointer

**Branch:** \`research/m3-ds3-compat-adapter\` (Draft PR #52).
**Reference source:** \`BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d\`.
**Status:** an opt-in **research callback-correlation prototype**, not production DS3 admission or a live M3 patch. All real Bluetooth/security flags and the normal bonded HID pathway stay unchanged when the feature flag is OFF.

## Source-proven reason the earlier ACL epoch observer is insufficient

At [\`l2c_csm.cc:299–310\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_csm.cc#L299-L310), incoming BR/EDR Classic HID \`PSM 0x11\` / \`0x13\` calls \`btm_sec_l2cap_access_req(bda, psm, false, &l2c_link_sec_comp, p_ccb)\`. The \`p_ref_data\` is the **raw CCB address**.

[BTM security requirement helper](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L1488-L1680) can:
- call the supplied callback **inline** (including immediate denial/success);
- invoke it with \`BTM_DELAY_CHECK\` while returning \`BTM_SUCCESS\`, while keeping a callback for subsequent security work;
- return \`BTM_CMD_STARTED\` and notify later; or
- defer work during ongoing pairing and resubmit pending L2CAP requests ([\`btm_sec_check_pending_reqs\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L2052-L2088)).

[Original \`l2c_link_sec_comp2\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_link.cc#L272-L326) checks the live CCB pointer and peer address, but **does not know which ACL generation existed when the BTM request originated**. A recycled CCB pointer and HCI handle can falsely appear to match after disconnect/reconnect. The previous [passive ACL epoch observer](M3-DS3-I2-I6-ACL-LIFETIME-EPOCH-OBSERVATION.md) records the current epoch, **not the immutable request epoch**.

## Concrete source-shaped patch and precedence

\`experiments/m3-ds3-cable-session/h618_request_bound_btm_callback_disabled.patch\` is a **second-stage overlay** against the result of applying:

1. \`h618_acl_epoch_observe_disabled.patch\` to the **exact pinned H618 source**;
2. \`h618_request_bound_btm_callback_disabled.patch\` afterward.

**Do not apply the second patch to pristine H618 alone.** Its 8 existing-source hunks were generated against the previously ACL-patched source and checked using source-content reconstruction. Both patches are guarded by \`RETROBOX_DS3_ACL_EPOCH_OBSERVE\` and \`RETROBOX_DS3_REQUEST_REF_OBSERVE\`, respectively. Both macros remain **undefined** in the Android build. No target installation or compile-flag enablement is authorized.

| H618 source path | Opt-in research change |
|---|---|
| \`stack/l2cap/retrobox_request_refs.h\` | Fixed-capacity 64-slot \`RequestRefPool\`, with slot addresses **never reused for process lifetime** |
| \`stack/l2cap/l2c_csm.cc\` | Only incoming Classic HID 0x11/0x13 gets a freshly minted opaque BTM callback reference, **if** live ACL epoch and table capacity are available; otherwise passes to the original code |
| \`stack/l2cap/l2c_link.cc\` | New guarded callback checks stored handle, LCB pointer, CCB pointer, original epoch and PSM against the **live** LCB/CCB. If current, forwards the **unchanged BTM status** to original \`l2c_link_sec_comp2\`; stale, duplicate or retired callbacks are dropped |
| \`stack/l2cap/l2c_utils.cc\` | Tombstone matching request references before CCB release/free-pool reuse or final LCB release |
| Existing ACL disconnect hook | Retires request refs before disconnect callbacks and possible LCB reuse |

The \`RequestRefPool\` has no authorization operation: it never creates a LinkKey, \`BOND_BONDED\`, HCI success, Java exception or \`UHID_CREATE\`.

### Important limitations of this design

- **Not production-capable as written.** The experimental 64 never-reused slots will eventually be exhausted; on exhaustion the guarded source patch **falls back to unchanged stock BTM callback behavior**, not a security bypass. Therefore the new correlation guarantee is **not universal** even with both flags ON. Never treat it as a security admission gate.
- **Not DS3-only.** Inbound HID PSM matching does not establish DS3 identity. Other incoming Classic HID devices could take the opt-in path, and callback filtering might disrupt normal devices. Thus enabling the flag is **NO_GO** until a properly scoped USB-enrollment provenance decision, deterministic full-target tests and owner approval exist.
- **Reentrancy, concurrency and teardown remain unproven in Fluoride.** The host class assumes all request lifecycle methods execute on the same serialized stack thread; runtime thread ownership and synchronous nested CCB release must be audited in the actual build. A BTM callback may arrive after a service change or a timeout, and the fixed pool is process-scoped only.
- **Epoch itself is not cryptographic identity.** It prevents an asynchronous callback from being associated with a different local ACL generation in the model; it cannot prove the radio station owns the USB-attended DS3. MAC, VID and PID are spoofable. USB-once enrollment is the Owner-approved UX; any bounded-risk wireless exception would still need separate explicit authorization.
- \`BTM_DELAY_CHECK\` is **not** terminal in the model; a subsequent result may follow. Any other BTM success/failure statuses are forwarded unchanged to the original L2CAP callback, which retains its stock normalization behavior.
- **Real M3 failure still exists.** The owner-confirmed capture shows HCI authentication \`0x22\` timeout and \`BOND_NONE\`; no demonstrated native security compatibility rule, Java event-bound grant, descriptor validation, Sony 0xF4 handling or wireless RetroArch success exists.

## Evidence and reproducibility

Committed:
- \`experiments/m3-ds3-cable-session/request_refs.h\`
- \`experiments/m3-ds3-cable-session/test_request_refs.cc\`
- \`experiments/m3-ds3-cable-session/h618_request_bound_btm_callback_disabled.patch\`
- \`experiments/m3-ds3-cable-session/verify_h618_request_bound_callback.py\`
- \`experiments/m3-ds3-cable-session/test_h618_request_bound_callback_patch.py\`
- Existing \`run_cpp_host_tests.sh\` invokes the new checks.

**Executed offline in local Linux G++ C++17:**
\`\`\`text
g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  -I. test_request_refs.cc -o test_ref && ./test_ref
92/92 PASS (opaque request refs, offline)

g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -I. test_request_refs.cc -o test_ref_san
ASAN_OPTIONS=detect_leaks=1 ./test_ref_san
92/92 PASS (opaque request refs, offline)
\`\`\`
The **92 are individual assertions, including 64 capacity insertions, not 92 independent test cases**. A separate local C++ stand-in of the same source-shaped wrapper was compiled with strict warnings and ASan+UBSan, **17/17 assertions PASS**, covering success, delayed then negative callback, duplicate callback, revoked CCB/LCB, epoch change, unrelated PSM and wrong peer address. These are all **mock execution** and do not establish actual H618 runtime correctness.

The committed Python source-extraction harness \`test_h618_request_bound_callback_patch.py\` is intended to compile the actual added wrapper from the patch with stand-in definitions. It is included in the host runner, but **that exact repository script was not independently executed in this increment**. The C++ wrapper stand-in itself was executed as described. Likewise, full-tree \`git apply --check\`, Soong build and any ARM32 M3 execution are **not yet performed**.

To rerun host checks in a repository checkout:
\`\`\`bash
cd experiments/m3-ds3-cable-session
python3 verify_h618_request_bound_callback.py
python3 test_h618_request_bound_callback_patch.py
\`\`\`

If the exact pinned full source tree is available, \`verify_h618_request_bound_callback.py --source-tree /path/to/BPI-H618-Android12\` optionally copies **only three** original H618 L2CAP source files into a temporary directory, applies the ACL observer patch **only in that scratch directory**, and checks whether the request-ref patch could then apply. It does **not** modify the BSP or the M3.

## Decision and next real gates

**PASS (offline):** original request identity encoded in a stable, nonreused process-local callback reference; host regressions, sanitizer checks and ordered source patch reconstruction.

**NO_GO:** enabling this research feature on M3, assuming a production safe pool/teardown lifecycle, trusting MAC/VID/PID as DS3 proof, weakening HID PSM security, faking bonding, Java admission changes, full Android source build, \`libbluetooth.so\` patch deployment, or declaring wireless gameplay.

The next milestone should focus on **USB enrollment provenance and the exact Native→Java event-bound admission contract**, plus understanding whether normal DS3 authentication can be made genuinely compatible *without* a trust exception. Any device-facing experiment requires separately reviewed operator supervision, independent recovery and explicit Owner authorization.

PR #52 remains Draft; PR #50 remains research archive, PR #51 remains source/build workstream, no merge or target changes.
