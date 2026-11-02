# I2/I6 — First source-shaped H618 checked byte-post seam (feature disabled)

Repository: \`franfran/android-bt-gamepad\`, Draft PR #52. Pinned public BSP reference \`BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d\`.

## Concrete artifact

\`experiments/m3-ds3-cable-session/h618_checked_bytes_disabled.patch\` is a **two-file source patch** against the pinned H618 \`system/bt\` tree:

1. \`system/bt/btif/include/btif_common.h\` — adds a conditional declaration for \`btif_transfer_context_checked_bytes\`.
2. \`system/bt/btif/src/btif_core.cc\` — adds a conditional implementation that accepts **only bounded pointer-free byte payloads**, makes an owned single-allocation copy, posts via existing \`do_in_jni_thread(base::Bind(&bt_jni_msg_ready,...))\`, propagates \`bt_status_t\`, and frees the outer message on reported enqueue failure.

Every addition is inside **\`#if defined(RETROBOX_DS3_PRIVATE_DESCRIPTOR_RESEARCH)\`**. This symbol is **not** enabled in any Android build configuration; the original \`btif_transfer_context\` behavior and **all original HID authentication/security/Java source** remain unchanged. The new helper is **not called** by BTA, so compiling the feature alone cannot establish CablePairing, authorize HID traffic or register a kernel device. The 4112-byte payload ceiling is a **host research fixture limit**, not a real DS3 Bluetooth descriptor bound.

### Why this seam matters

Pinned source shows the existing \`btif_transfer_context\` uses \`memcpy\` with optional deep-copy callback, ignores the result of \`do_in_jni_thread\`, and returns \`BT_STATUS_SUCCESS\`. \`bt_jni_msg_ready\` frees the outer message. A future private session descriptor event therefore needs **both** an owned byte snapshot and a checked post result before adding an asynchronous Java approval wait.

This prototype uses the **existing outer message allocation** and copies the entire serialized blob into its flexible parameter bytes. It deliberately has no extra heap pointer or STL container in the byte payload. A consumer must still parse, authenticate the **internal correlation ticket**, validate descriptor semantics, and reject stale events. A serialized handle and generation are not cryptographic proof of DS3 radio identity.

## Reproducibility and verification

\`\`\`bash
# From root of an EXACT checked-out H618 Android12 source tree:
git apply --check /path/to/android-bt-gamepad/experiments/m3-ds3-cable-session/h618_checked_bytes_disabled.patch

# DO NOT apply to a live device or build/enable the flag without separate review.
# To exercise the checked helper without Android:
cd /path/to/android-bt-gamepad
python3 experiments/m3-ds3-cable-session/test_h618_checked_bytes_patch.py
\`\`\`

The Python test extracts the **actual added helper code from the committed .patch file** and compiles it against stand-in native JNI message types, checked fake scheduler, and malloc/free routines under \`-std=c++17 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined\`. It tests bad pointer/length inputs, scheduler-rejected post freeing resources, accepted post retaining copied bytes after source mutation, and exactly-once message destruction.

**Completed evidence:**
- Both hunk context blocks independently matched the exact pinned upstream GitHub files, without guessing line contents. **Full-tree \`git apply --check\` was not run** because a full matching BSP checkout is not present in this execution environment.
- An isolated Linux G++ mock-scheduler harness compiled the **same newly added C++ helper** under strict flags and ASan+UBSan; **12/12 assertions PASS**.
- The repository Python extractor/test is committed and wired into \`run_cpp_host_tests.sh\`. **That exact Python runner has not independently executed in this turn**; do not misrepresent its status as a full native integration/build result.

## Proof boundaries and next implementation steps

- **PASS:** exact checked byte-post helper source seam, disabled-by-default source patch, reference source context check, local stand-in C++ allocation/post-failure behavior.
- **NOT PROVEN:** full Android C++ compile with real Chromium base/task runner and ABI; queue refusal shutdown semantics under OEM JNI thread; native BTA-allocated DS3 descriptor envelope with HID handle **and actual ACL/HID lifecycle generation**; Java private session-bound response; HID descriptor/report validation; bounded-risk Bluetooth security exception; M3 wireless gameplay.
- **Safety:** preserve normal bonded HID. Never set security service flags globally to zero, fake bonds or claim authentic radio identity from a MAC. Existing USB DS3 working in RetroArch remains the baseline. Source patch is **research only**, no device operations, no installation, firmware changes, service restart, or PR merge.
- **Next:** source design for a private BTA candidate event and Java response mechanism (including shutdown, backpressure, timeout and no deadlock). Then obtain a real matching source tree/build and separate owner scoped security-risk approval before considering any target-side use.

Do not interpret an unconfigured build macro as sufficient live rollout protection: no target-side test is authorized, and source-level code review remains required before enabling it.
