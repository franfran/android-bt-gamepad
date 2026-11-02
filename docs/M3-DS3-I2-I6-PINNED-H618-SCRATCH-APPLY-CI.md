# I2/I6 — Verified pinned H618 source overlay CI, without a full Android BSP

**Status:** offline source compatibility confirmed for three *independent*, disabled research patches. **Not** an Android build, M3 compatibility, or deployment authorization. Source branch: Draft PR #52. Full BSP/reproducible ARM32 build remains Draft PR #51.

## Why this milestone matters

Previous PR #52 evidence verified individual hunk context by extracting exact pinned GitHub source. That did **not** prove Git could apply the entire unified diff. On 2026-11-02 the new [RetroBox Pinned H618 Patch Apply (Host Only) workflow](../.github/workflows/retrobox-pinned-h618-apply.yml) ran a real `git apply --check` against a fresh scratch directory containing the exact required upstream files.

The first run, [41455628135](https://github.com/franfran/android-bt-gamepad/actions/runs/41455628135), exposed a **real Java patch failure at `HidHostService.java:977`** despite all earlier per-hunk checks. Cause: the last diff hunk included a fictitious blank context line beyond upstream EOF (a Python `split("\n")` artifact). Commit `c5831c6` removed this context and fixed the old/new hunk counts.

The successful complete run, [41456280613](https://github.com/franfran/android-bt-gamepad/actions/runs/41456280613), verified all **five** original Git blob SHA-1 values from pinned source `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`, then tested three independent profiles:

| Profile | Pinned original files | Result |
|---|---|---|
| auth | `system/bt/stack/btm/btm_sec.cc`, `system/bt/btif/src/btif_dm.cc` | `GIT_APPLY_CHECK_PASS` |
| jni | `packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp`, `packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java` | `GIT_APPLY_CHECK_PASS` |
| uhid-v3 | `system/bt/btif/co/bta_hh_co.cc` | `GIT_APPLY_CHECK_PASS` |

The combined log reports `SOURCE_PATCH_CHECKS_PASS: auth,jni,uhid-v3`.

**Additional true CI execution (same successful run):** the exact committed source-extracted JNI C++ test compiled with strict GCC and AddressSanitizer+UBSan, **9/9 PASS**; the exact committed Java Handler test compiled using `javac`, **9/9 PASS**. The earlier legacy-auth CI also executes **13/13** synthetic-only trace analyzer tests. None of these are an Android stack compile.

## Reproduce

Code: `experiments/m3-ds3-cable-session/verify_h618_pinned_git_apply.py`.

```bash
python3 experiments/m3-ds3-cable-session/verify_h618_pinned_git_apply.py --profile all
# Or restrict to: auth, jni, uhid-v3
```

The script downloads five explicitly allowlisted public files over HTTPS via `raw.githubusercontent.com`, **at the immutable upstream commit**, computes their actual Git blob SHA-1 using Git's blob-object construction, rejects any mismatch or oversized input, then creates a disposable scratch root and calls `git apply --check`. It **does not** fetch the entire BSP, update the source, run a compiler against Android source, access credentials, or modify any Android device. The workflow uses only `contents: read`, no persisted GitHub credentials, and `ubuntu-latest`.

`git apply --check` checks each patch **separately** against pristine pinned files. Profiles are mutually independent; do not stack patches into one target build without a separately tested patch order. The v1/v2/v3 UHID prototype patches are alternative research versions, **not** a stack to merge.

## Precisely what was and was not established

**PASS:** Public pinned source identity, Git-level applicability of the above three overlays, extraction and syntax/runtime smoke of selected mock JNI/Java functions, and regression CI. No source modification semantics were accepted as a production Bluetooth security policy.

**NOT PROVEN / NO_GO:**
- A complete, reproducible Android 12 BSP with build/envsetup.sh, build/soong/soong_ui.bash and necessary proprietary/vendor pieces. PR #51's full build preflight previously observed a **missing** `/data/android/BPI-H618-Android12` checkout on the operator's host. Source snippets do not substitute for Android Soong and the correct ARM32 target.
- Host-translated observer patches under actual H618 C++ compilation, Java JNI registration in a built APK, Java service lifecycle with real Binder/callback concurrency, BTM ↔ Java admission, real on-air DS3 PIN/authentication, and final `libbluetooth.so` ELF ABI agreement.
- A security exception for unbonded DS3. The native auth trace is **observation only** and the JNI callback is **deny only**. The standalone UHID v3 patch **would block normal bonded HID if enabled** because there is no real standard-authentication classifier or `PermitStandard` source caller.
- Any OTA update, SELinux change, module injection, live Bluetooth service restart, pairing session, or M3 runtime change. None was performed or authorized.

## Next decision checkpoint — correction of PR #52 scope

**PR #52 does NOT require obtaining the full Android BSP as a prerequisite.** Its explicit purpose is to determine whether a removable plugin or independent compatibility daemon can enable DS3 wireless support **without replacing OEM `/system/lib/libbluetooth.so`**. Full BSP/Soong/ARM32 native library replacement is PR #51's **separate** source-first route, not the next PR #52 task.

**Continue PR #52 in the following order:**

1. **Architecture A / I1 — Actual extension surface:** inspect the pinned Fluoride/OEM Bluetooth stack for a supported plugin registration/loading interface, ownership handoff and versioned callback/ABI. Distinguish vendor HAL hooks from a Classic HID host plugin; do not assume an arbitrary `dlopen` or a debugger-injected .so is a supported extension.
2. **Architecture B / I2 — Standalone daemon transport ownership:** determine whether a legitimate root/system service can obtain exclusive DS3 Classic HID L2CAP PSM 0x11/0x13 and HCI/controller access without conflicting with the already-running OEM Fluoride stack or weakening its security. If exclusive ownership is not available, reject this architecture rather than pretending UHID emulation fixes authentication. Identify whether Android platform APIs or OEM service features could delegate a connection.
3. **Architecture D / I4 — Existing supported APIs/config:** inspect actual OEM API/configuration for per-device cable enrollment, genuine pairing/bond behavior, virtual-unplug handling and required privileges; reject MAC-only spoofed trust or a global low-security HID policy.
4. **I3 — Input bridge only after real transport proof:** verify kernel `uinput` support and permissions vs confirmed UHID support, Android InputReader/RetroArch event recognition, and report/rumble lifecycle. A valid `UHID_CREATE` path is not a substitute for successful Bluetooth authentication.
5. **I6 — Architecture decision:** publish a GO / CONDITIONAL / NO_GO table for A, B, D and fallback C, with exact evidence and the smallest safe offline PoC. **Only option C** (minimal source modification) or separately chosen PR #51 patched-library approach should trigger a full BSP build requirement.

The three pinned-source patch applicability results above remain useful **architectural research/reference only**. They do not establish a plugin interface or a viable standalone daemon. Do not redirect PR #52 to recompiling `libbluetooth.so` merely because these source patches apply.

**Cross-workstream boundaries:** PR #50 reverse engineering archive remains unmerged; PR #51 full source/build remains Draft; PR #52 authentication/Java/UHID source research stays Draft. Owner review required for merges or device-facing changes.
