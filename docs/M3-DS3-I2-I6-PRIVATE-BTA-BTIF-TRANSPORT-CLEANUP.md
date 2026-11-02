# I2/I6 — Private BTA→BTIF descriptor transport and cleanup proof (host only)

**Scope:** pinned [H618 Android 12 source \`250eabfc529518b7f26432663ed0a867ab2f625d\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/tree/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt), and standalone C++17 host research on PR #52. This is **not an integration patch**. Normal bonded HID must remain untouched. The spoofable USB-cable-pairing radio claim, genuine Native/Java grant, actual descriptor parser and build compatibility are not solved here.

## Source observations: producer, copy, callback and cleanup

1. [\`bta_hh_get_dscp_act\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L905-L911) produces \`BTA_HH_GET_DSCP_EVT\` from \`&p_cb->dscp_info\`, omitting the already-known HID handle and the connection epoch. **Do not enlarge the old struct while retaining this cast**.
2. [\`bte_hh_evt\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1105-L1133) supplies \`sizeof(tBTA_HH_DEV_DSCP_INFO)\` and no deep-copy callback to [\`btif_transfer_context\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_core.cc#L127-L151). The latter copies fixed-size bytes via \`memcpy\` when copy callback is NULL; **the referenced descriptor bytes are not owned by this message**.
3. [\`bt_jni_msg_ready\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_core.cc#L219-L223) calls the consumer and then \`osi_free(p)\`. It does **not** recursively release any heap buffer that a hypothetical new envelope points to. Thus a separate descriptor allocation requires explicit cleanup; otherwise adopt a bounded contiguous allocation with inline bytes and a correct post/consume contract.
4. [\`do_in_jni_thread\` / \`btif_transfer_context\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_core.cc#L127-L165): the current transfer wrapper calls \`do_in_jni_thread(...)\` and unconditionally returns \`BT_STATUS_SUCCESS\`, even though the posting helper itself may report \`BT_STATUS_FAIL\`. The original wrapper is **not proven to offer reliable enqueue failure reporting or cleanup** for a proposed new private path. An implementation must explicitly verify queue posting result and ownership rollback; the model below does not exercise actual Android JNI scheduler failure.
5. Source precedent: [\`BTA_HhAddDev\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_api.cc#L305-L334) uses a different contiguous BTA maintenance message with appended descriptor bytes. This is a **pattern reference**, not evidence that GET_DSCP already copies bytes or that its event layout can safely be expanded.
6. [\`btif_hh_upstreams_evt\` descriptor branch](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L951-L984) chooses \`p_curr_dev\`, a mutable global device selector, then sends \`UHID_CREATE\`. Cross-device attribution risk is a **plausible interleaving hypothesis**, not a proven real M3 exploit.

## New executable host-only prototype

- \`experiments/m3-ds3-cable-session/private_descriptor_transport.h\`: \`PrivateDescriptorTransport\` stores **owned \`std::vector<uint8_t>\` bytes** with \`DescriptorTicket{handle,generation}\` at enqueue, bounded by a fixture length and pending count. Rejects invalid/duplicate events. \`Cancel(ticket)\`, \`CancelAll()\` and one-shot dequeue manage cleanup with RAII.
- \`experiments/m3-ds3-cable-session/test_private_descriptor_transport.cc\`: host tests for producer-buffer mutation, FIFO interleaving, duplicate rejection, cancellation, epoch reuse, stale delivery, malformed input, queue backpressure, and an actual integration adapter to the existing \`DescriptorGate\` C++ host model: queue dispatch does **not** permit \`UHID_CREATE\` before the separately modeled Java admission; reused handle with stale generation is rejected.
- \`experiments/m3-ds3-cable-session/run_cpp_host_tests.sh\` updated to compile/run both existing \`test_session_descriptor_envelope.cc\` and new transport suite.

Verification in isolated Linux host directory, GCC C++17 strict flags:
\`\`\`text
g++ -std=c++17 -Wall -Wextra -Werror -pedantic test_private_descriptor_transport.cc session_descriptor_envelope.cc -o test
./test
37/37 checks PASS (host-only copy/queue model)

g++ -std=c++17 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer test_private_descriptor_transport.cc session_descriptor_envelope.cc -o test_san
ASAN_OPTIONS=detect_leaks=1 ./test_san
37/37 checks PASS (host-only copy/queue model)
\`\`\`

**37 checks** = individual assertions in a few grouped scenarios, **not** 37 independent test methods. They prove only local model behavior; all descriptors are toy data and authorization predicates are symbolic.

## Critical integration constraint: std::vector is NOT an Android wire format

Never pass the C++ prototype's \`DescriptorEnvelope{std::vector<...>}\` directly through \`btif_transfer_context(..., NULL)\` or a C bytewise \`memcpy\`: this would copy a nontrivial C++ container's internal pointers, causing aliasing and lifetime corruption.

If eventually authorized and buildable, a source-integrated solution needs **one** of:
- a private, trivially copyable event header plus strictly bounded **inline descriptor bytes** in an owned contiguous allocation and a correctly specified transfer/cleanup path, or
- a private heap-owned descriptor envelope with custom deep-copy and explicit free on all success, rejection, cancellation and posting-failure paths.

Both require immutable session generation minted from actual ACL/HID lifecycle, not inferred from MAC or pointer identity; handle wrapping/reuse must be tested. Existing BTA \`tBTA_HH_DEV_DSCP_INFO\` and public HAL/JNI signatures must not silently be enlarged. If a private event or compiler flag is added, it should be disabled by default, preserve bonded HID and be isolated to the exact DS3 cable candidate with clear rollback.

## Next proof gate

1. Trace the exact native event registration and callback cleanup for a **private** message, including scheduling/failure semantics; no reliance on the current shallow-copy wrapper's unconditional SUCCESS.
2. Define a source-integrated **POD inline-buffer envelope prototype** (still offline), test byte bounds, callback cancellation and ownership destruction. Use no pointer/heap aliases in bytewise-transferred payload.
3. Separately design event-bound Native↔Java admission response, because JNI currently forwards only \`(address,state)\`, and Java Handler admission can occur after \`UHID_CREATE\`.
4. Keep descriptor validation/report validation before kernel UHID for the candidate path; no actual M3 source binary, target compilation, HCI link or successful wireless RetroArch state has been demonstrated.

**Decision: host-model copy/cleanup verification PASS; real BTA→BTIF integration and live Bluetooth security exception remain NO_GO.** No M3 operations or changes to PR #50/#51.
