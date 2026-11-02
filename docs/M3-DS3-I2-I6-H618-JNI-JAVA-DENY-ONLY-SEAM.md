# I2/I6 — H618 HID Host JNI ↔ Java deny-only source seam

**Project:** RetroBox iMETBOX M3 DS3 wireless, Draft PR #52 on \`research/m3-ds3-compat-adapter\`. Reference pinned public tree: \`BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d\`.

**Decision:** This is a **source-shaped, disabled-by-default JNI/Java callback skeleton**, NOT a working Native/Java approval bridge or a DS3 wireless patch. It makes **no BTM security decision**, **no JNI-held approval grant**, **no UHID_CREATE gating** and **no USB I/O**. No device operations or PR merge authorized.

## 1. Source verification

Pinned source:
- [HID Host JNI callback](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L52-L71) calls Java \`onConnectStateChanged(address,state)\`. The original [GetMethodID \`([BI)V\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L193-L198) and [JNI sMethods registry](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L510-L529) do not have a private candidate request or response.
- [Java onConnectStateChanged](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L802-L807) queues \`MESSAGE_CONNECT_STATE_CHANGED\`, and its [Handler](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L185-L207) runs \`okToConnect()\` only after the native HAL CONNECTED notification. [\`okToConnect()\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L892-L919) preserves quiet-mode, \`BOND_BONDED\` and connection-policy checks.
- [BTIF descriptor handler](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L950-L985) can send HID information to UHID without waiting for an event-bound Java approval. This is a source-level ordering concern, NOT proof of a real device exploit.

## 2. Exactly what the new disabled patch adds

[\`h618_jni_java_deny_only_disabled.patch\`](../experiments/m3-ds3-cable-session/h618_jni_java_deny_only_disabled.patch) modifies only these two paths:

1. **\`packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp\`:** under an **unset** C++ compile flag \`RETROBOX_DS3_JAVA_ADMISSION_RESEARCH\`, register private JNI method \`onRetroboxHidCandidate([BIJJ)V\`, add a no-caller \`retrobox_hid_candidate_observe(address,handle,aclEpoch,requestId)\` helper, and private Java response JNI registration \`retroboxAdmissionDecisionNative(IJJZ)Z\`.
   - The JNI helper checks null address and invalid nonpositive ticket members; uses existing callback mutex and CallbackEnv; sends asynchronous Java notification with address bytes and ticket fields.
   - **No trusted Native producer is wired to this helper.** Handle/ACL epoch/request ID passed to it have no verified provenance and cannot be used for admission.
   - \`retroboxAdmissionDecisionNative\` deliberately **always returns JNI_FALSE** (including if Java supplies \`approve=true\`). There is **no pending Native request registry to update**, so even \`approve=false\` is presently only a *negative acknowledgment attempt*, **not** an effective Bluetooth disconnect/veto. Nothing gets newly authorized.
   - Original \`connection_state_callback\`, JNI registration and public HAL interface remain unchanged when the flag is OFF.

2. **\`packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java\`:** add an internal \`MESSAGE_RETROBOX_CANDIDATE\` Handler case, ticket-bearing value object that clones the address, and \`onRetroboxHidCandidate(address,handle,epoch,req)\`.
   - **This method is unreachable** unless an explicitly built private JNI research emitter calls it; the existing native/HAL connection callback is unchanged.
   - Java event is queued and checks its **Java service generation** before attempting to reply. \`start()\` increments the generation, and both \`stop()\` and \`cleanup()\` increment it and remove queued candidate messages. Stale Java Handler events do not become current session responses.
   - The Handler sends **\`approve=false\` only**. No Java trust in USB F2/F5, MAC match, BLE name, device VID/PID or existing BOND_BONDED checks is relaxed.
   - The Java native declaration exists in compiled class source even while research macro is OFF, but is never called because no corresponding Java candidate event is emitted. Its registration is guarded in JNI; **do not separately enable Java event creation without matching JNI build**.

## 3. Verification actually completed

**Patch integrity:** all **11 original source hunks** (five JNI, six Java) were checked line-by-line against the exact pinned H618 upstream GitHub file, with expected unified diff old/new counts and cumulative line offsets. No original source lines removed. The C++ feature macro remains undefined in the Android build. Full Android Soong/Java/ARM32 runtime build and full BSP checkout have NOT been run. However a real pinned-source, scratch-tree `git apply --check` has now passed in CI (see update below).

**Host smoke checks using manually extracted exact added function blocks** in isolated Linux stand-ins:
- Java \`javac -Xlint:all\` source-shaped class/Handler: **9/9 PASS**. Includes async queueing, copying mutable address input, stale service generation, invalid ticket suppression, no native availability, queue removal, and approve=false.
- C++ \`g++ -std=c++17 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined\` using stand-in JNI types and *the same added C++ functions*: **9/9 PASS**. Includes bad pointer/ticket, callback invocation, native reply never approving even when passed true, and absent callback object.
- These are **isolated source-shaped smoke tests**. They cannot verify Java+JNI runtime together, GKI/H618 full build, service shutdown races, native callback thread behavior or an effective security denial.

**Committed reproducibility tools**:
- \`experiments/m3-ds3-cable-session/test_h618_jni_java_deny_only_patch.py\` extracts Java additions from the actual committed patch and compiles them with host \`javac\`, plus static JNI signature/guard checks. Java JDK required.
- \`experiments/m3-ds3-cable-session/test_h618_jni_candidate_cpp_patch.py\` extracts C++ observer + always-denied JNI reply from the actual committed patch, compiles against stand-in types and runs ASan+UBSan. GCC required.
- \`run_cpp_host_tests.sh\` now invokes the C++ extractor; Java extractor is separate because not all minimal Ubuntu hosts have \`javac\` installed.

**Updated CI verification (2026-11-02):** [Pinned H618 Patch Apply run 41456280613](https://github.com/franfran/android-bt-gamepad/actions/runs/41456280613) verified the exact upstream Git blobs and performed a real `git apply --check` of the committed JNI/Java patch (**PASS**). An initial CI failure found a fictitious EOF blank-context line in the Java patch, corrected in commit `c5831c6`. The same CI run executed the **exact committed** source-extracted JNI C++ test with G++ ASan/UBSan (**9/9 PASS**) and Java test with javac (**9/9 PASS**). Host mocks do not establish Android JNI compile, actual Native admission, or M3 operation. Reproduce:
\`\`\`bash
python3 experiments/m3-ds3-cable-session/test_h618_jni_candidate_cpp_patch.py
python3 experiments/m3-ds3-cable-session/test_h618_jni_java_deny_only_patch.py
\`\`\`

## 4. Why NO_GO is unchanged

**This is not even a working denial/veto**, because the private JNI function has no Native pending-registry implementation, and the existing BTIF \`BTA_HH_GET_DSCP_EVT\` / \`UHID_CREATE\` path remains unaltered. Enabling only the flag would not ensure pre-UHID gating.

**Must-have before any real admission:**
1. Stable, immutable ACL/HID request ticket generated by a trusted Native producer, with verified BTM/HCI origin and asynchronous callback lifetime. Current PR #52 source overlay uses opt-in 64 nonreused request slots and has a documented exhaustion / non-DS3-wide PSM exposure issue.
2. Dedicated Native pending-request registry and explicit *actual* success/failure acknowledgments tied to one live session; service generation and shutdown cancellation on both JNI and Java sides; no JNI thread waiting synchronously on Java Handler.
3. Correct per-device descriptor correlation, owned bytes and validated report input before **\`UHID_CREATE\`**/**\`UHID_INPUT\`**, with normal bonded HID kept on existing path.
4. No assumption that cable F2/F5 plus a matching MAC is cryptographic identity; user-approved USB-once setup is an enrollment **candidate**, never itself a grant. A scoped risk decision and genuine Native authentication compatibility still must be researched.
5. Pinned source **is not known ABI-identical to original M3 ARM32 Bluetooth**; complete matching Android BSP compilation from PR #51 is NO_GO until build dependencies/source are available. No live M3 edits, APK deployment, service restart, \`.so\` patch, pairing attempt or PR merge authorized.

**Recommended follow-on:** build and test a **pure Native pending-request registry** with checked enqueue failure and Java service invalidation; prove no Java response can be replayed to newly reused ACL session, and no candidate UHID occurs before actual admission. It should remain dormant until a full code review and compatible build.
