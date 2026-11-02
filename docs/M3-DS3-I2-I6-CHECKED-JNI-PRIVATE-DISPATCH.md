# I2/I6 — Checked private JNI descriptor dispatch: source-integration contract

**Workstream:** PR #52 only, offline prototype. Original DS3 wired input on M3 RetroArch is already PASS; desired UX remains a single USB setup then Bluetooth wireless PS-button connection/reconnect. No M3 operation, Bluetooth security exception, target APK/native binary, or PR merge is authorized.

**Pinned source:** [BPI H618 Android12 commit \`250eabfc529518b7f26432663ed0a867ab2f625d\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/tree/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt).

## A. Exact source-level constraint

- [\`bta_hh_get_dscp_act\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L905-L911) emits the existing descriptor callback as a cast of \`&p_cb->dscp_info\`; this original structure is not an event-bound envelope. Do **not** extend it and blindly read beyond the existing producer object.
- [\`bte_hh_evt\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1105-L1133) uses \`btif_transfer_context(..., nullptr)\` with \`sizeof(tBTA_HH_DEV_DSCP_INFO)\` and no deep copy of \`descriptor.dsc_list\`.
- [\`btif_transfer_context\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_core.cc#L127-L151) allocates the outer message, copies fields/bytes, posts through \`do_in_jni_thread\`, **ignores its result**, and returns \`BT_STATUS_SUCCESS\` unconditionally. [\`do_in_jni_thread\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_core.cc#L155-L170) may return \`BT_STATUS_FAIL\` when thread scheduling fails.
- [\`bt_jni_msg_ready\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_core.cc#L219-L223) calls the callback and releases only its **outer** message object. It does not have a generic recursive cleanup mechanism for separate descriptor allocations.
- [\`BTIF BTA_HH_GET_DSCP_EVT\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L951-L984) uses shared \`p_curr_dev\` and can write \`UHID_CREATE\` before the independent Java Handler's \`okToConnect\` decision. Neither callback gives an immutable ACL/HID epoch.
- Normal BTA HH callback signature is \`void(tBTA_HH_EVT,tBTA_HH*)\` ([\`bta_hh_api.h:299–318\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/include/bta_hh_api.h#L299-L318)). There is currently **no accepted private descriptor event ABI** for the new CablePairing candidate.

## B. Tested host-only checked-dispatch prototype

New:
- \`experiments/m3-ds3-cable-session/private_checked_dispatch.h\`
- \`experiments/m3-ds3-cable-session/test_private_checked_dispatch.cc\`
- \`experiments/m3-ds3-cable-session/run_cpp_host_tests.sh\` updated.

\`CheckedPrivateJniDispatcher\` models an owner-enveloped task whose descriptor bytes are **serialized and copied at Submit**, placed into an individually owned task, and destroyed through RAII on every path. The scheduler acceptance boolean is a **mock injectable failure**, NOT a real call to Android \`do_in_jni_thread\`. This is fundamentally different from calling existing \`btif_transfer_context\` and hoping for a reliable error.

**Local direct execution:**

\`\`\`text
g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
    session_descriptor_envelope.cc test_private_checked_dispatch.cc -o checked_test
./checked_test
12/12 PASS (checked private JNI dispatcher model)

g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    session_descriptor_envelope.cc test_private_checked_dispatch.cc -o checked_san
ASAN_OPTIONS=detect_leaks=1 ./checked_san
12/12 PASS (checked private JNI dispatcher model)
\`\`\`

Twelve named tests: pre-copy producer mutation, successful task cleanup, scheduler refusal cleanup, full-queue backpressure cleanup, malformed input, cancel by session, disconnect/reuse stale epoch, Java deny before pending descriptor, Java-first / descriptor-first ordering, concurrent devices, consumer rejection cleanup, shutdown flush. All are host simulations, without actual Bluetooth or HAL interactions.

## C. Minimum source-integration contract (NOT IMPLEMENTED)

Only after a *separately reviewed, scoped* source implementation becomes buildable:

1. **Private candidate-only emitter in BTA**. Build from a validated current BTA HID control block; attach HID handle, a monotonic ACL/HID session epoch minted at an actual lifecycle point, and bounded copied descriptor. Do not infer epoch from MAC, pointer, or handle alone; and never extend the original \`tBTA_HH_DEV_DSCP_INFO\` object by reinterpret cast.
2. **Private BTIF scheduler, not the existing shallow wrapper**. Use an ownership-safe task/closure with a checked \`do_in_jni_thread\` result, or a narrowly written checked internal equivalent; both success and failure must release the private task exactly once. Prefer a move-only owned event, no C++ \`std::vector\` passed to raw \`memcpy\`. The task itself may own a vector, provided the vector is never bytewise-copied. All code paths (thread shutdown, post failure, java veto, stale-generation drop, timeout) require an explicit ownership proof.
3. **Recheck at consumption**. Locate exact session by handle+epoch and verified current link; do not use shared \`p_curr_dev\` to authorize. Stage owned bytes until a separate Java admission response exists; deny \`UHID_CREATE\` without BOTH gates. Ensure no deadlock waiting for Java on the Bluetooth/JNI dispatch thread.
4. **Java internal admission bridge**. Existing JNI callback \`onConnectStateChanged([BI)V\` is address/state-only. A new internal, event-bound callback/response mechanism would be needed, but must preserve public HAL API, quiet mode, forbidden connection policy and existing normal \`BOND_BONDED\` flow. **Java MAC allowlisting is not equivalent**.
5. **Pre-kernel input guards**. Validate actual Bluetooth DS3 descriptor (currently missing fixture) before \`UHID_CREATE\`, and validate input reports before \`UHID_INPUT\`; revoke on disconnect. Kernel \`CONFIG_HID_SONY=y\` and \`CONFIG_UHID=y\` are supported by the uploaded config, but runtime \`hid-sony\` binding, Sony 0xF4 completion and working wireless RetroArch remain unverified.
6. **Fail closed for CablePairing only**, leave ordinary bonded HID paths unchanged. New functionality disabled by default; no global HID mask reduction, fake BOND_BONDED, forged BTM authentication or adapter-wide low security. The remaining USB-enrollment/MAC-spoofing bounded risk still requires explicit Owner acceptance before any target changes.

## D. Decision / next real blocker

**Offline host transport: PASS** for checked ownership/refusal/cancellation semantics. **True source integration: NOT BUILT / NOT PROVEN**, because the exact private native BTA↔BTIF event API, per-link epoch mint, Java response transport, and matching Android build inputs are not yet established. The PR #51 BSP build preflight previously failed due to missing full source on that host; don't promise drop-in \`libbluetooth.so\`.

**Next engineering increment:** choose one narrowly-scoped internal callback pattern with actual C++ production types; assess deadlock/ordering in \`do_in_jni_thread\` versus Java Handler response; produce an auditable *disabled-by-default patch sketch* for exact pinned source without making live-device modifications. Keep PR #50 research archive and PR #51 source-first build work separate.
