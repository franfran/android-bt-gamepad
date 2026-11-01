# M3 DS3 Source-first: technical handoff and implementation contract

**Created 2026-11-01 · independent branch from `main` · initial scope: research, source attribution, patch design and OFFLINE build only.**

## 0. Read this first

- Source of truth for prior detailed reverse engineering: **[PR #50](https://github.com/franfran/android-bt-gamepad/pull/50)**, head `plan/m3-ds3-privileged-pin-helper` (intentionally kept unmerged as research baseline).
- PR #50's source-first feasibility research: [source-first feasibility on PR #50 branch](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-SOURCE-FIRST-FLUORIDE-BUILD-FEASIBILITY.md).
- PR #50's exact native UHID disassembly: [kernel UHID SET_REPORT gate](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-KERNEL-UHID-SETREPORT-GATE.md).
- PR #50's fail-closed **host-only** model: [transaction model](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/experiments/m3-hid-apk/set_report_transactions.py) and [tests](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/experiments/m3-hid-apk/test_set_report_transactions.py). Last run: eight tests passed; this proves neither native callback order nor safe runtime deployment.
- Starting from `main` keeps review clean. This handoff is self-contained; do NOT require future chats to remember unpublished details or to merge PR #50 first.

## 1. Actual project objective and constraints

Enable a **genuine Sony DualShock 3** to work wirelessly over the iMETBOX M3's **built-in Classic Bluetooth** with RetroArch after a one-time **USB `sixpair` enrollment** (controller's master address set to the M3's local Bluetooth address). User already confirmed wired USB controller **completely works in RetroArch, including buttons**. Do **not** waste time repeating wired controller input tests. One-time USB enrollment is acceptable; goal afterward is press PS button for wireless operation without manual PIN/bonding interaction.

Target M3: Oranth/iMETBOX M3 (International), Allwinner H618, Android 12 `SP1A.211105.004` userdebug, Bluetooth process `com.android.bluetooth` UID 1002, existing `/system/lib/libbluetooth.so` **ELF32 ARM**; Wi-Fi ADB is preferred, physical USB recovery cable available. Android security/kernel context and original APK are documented in PR #50 / earlier handoffs.

**Never** flash firmware, replace `/system/lib/libbluetooth.so`, restart the live Bluetooth stack, change global HID security, inject hooks, replace APK, manipulate AVB/SELinux or merge without *separate explicit owner approval*. Prior runtime S7-C4C gate stays **NO_GO**. Do not edit `main` as part of this work.

## 2. Main breakthrough: matching publicly available source

**Public H618 Android 12 BSP:** https://github.com/BPI-SINOVOIP/BPI-H618-Android12

Important source files (confirmed through direct repository reads):
- `system/bt/btif/co/bta_hh_co.cc`: `UHID_SET_REPORT` ingress, `UHID_FEATURE` GET request-ID queue, and **exact original log text** `%s: Error: UHID_SET_REPORT_REPLY not supported` in `bta_hh_co_set_rpt_rsp(uint8_t dev_handle, uint8_t status)`.
  - In observed repository branch, GET around line 153 enqueues `ev.u.feature.id` in `get_rpt_id_queue`.
  - SET around line 165 forwards report via `btif_hh_setreport(...)` but does **not** queue `ev.u.set_report.id`.
  - Callback around line 564 logs unsupported instead of writing `UHID_SET_REPORT_REPLY`.
  - The SET ingress is wrapped in `#ifdef OS_ANDROID`; inspect exact build flags and kernel expectations before editing.
- `system/bt/bta/hh/bta_hh_act.cc` around line 662: `BTA_HH_SET_RPT_EVT`, `bta_hh_co_set_rpt_rsp`, application callback, then `p_cb->w4_evt=0`.
- `system/bt/stack/hid/hidh_conn.cc` around line 100: `L2CA_Register2` for HID control/interrupt PSM `0x11`/`0x13` with global `BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT`. **Do not blindly remove or globally weaken these flags.**
- `system/bt/main/Android.bp` around line 68: `cc_library_shared { name: "libbluetooth", ... }`, links `libbtif`, `libbt-bta`, `libbt-stack` and other dependencies; this is a genuine path to compile an Android shared object.
- Legacy Fluoride AOSP comparison: https://android.googlesource.com/platform/system/bt/ (pin a specific commit before working). AOSP and BSP branches may differ; source correspondence is **very strong in the UHID module**, **NOT proven byte-identical or ABI-compatible** across the whole library.

**First action in new workstream**: pin exact SHA of public BSP (and corresponding `system/bt` tree), record build revision/toolchain and compare source features/struct layout to the owner-original ELF, rather than relying indefinitely on moving `master`.

## 3. Original M3 native ELF immutable identity

Owner uploaded original 2024 `m3-original-2024-libbluetooth.so` into previous chat. It is **not committed**; request a re-upload only if exact binary needed for a local comparison and not mounted.
- SHA256: `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`
- ELF32 little-endian ARM EABI5, Android API 31, stripped.
- Build ID: `0d29a62178e43066e018216c1f1d5b18`
- `.text`: ELF VMA = file offset + `0x1000` in the inspected code region; Thumb symbol low bit denotes Thumb state, not byte address. **Do not use these VMAs as live patch offsets.**
- Original `M3-Bluetooth.apk` SHA256 `d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f`.
- M3 kernel configuration: `CONFIG_UHID=y`, `CONFIG_HID_SONY=y`, `CONFIG_HIDRAW=y`, `CONFIG_INPUT_EVDEV=y`. Actual Bluetooth kernel bind/DS3 input remains unverified.

## 4. Three *independent mandatory* compatibility gates

**A — Native HID/L2CAP authentication, before input.**
- M3 native registers PSM `0x11` (control) and `0x13` (interrupt), security mask `0x36` (authentication + encryption in context), with security path at native `btm_sec_l2cap_access_req` call VMA `0x2897b4` from `l2c_csm_execute`.
- Historical capture showed HCI Authentication Requested opcode `0x0411` and Authentication Failure `0x22` (timeout). This happens *before* UHID probe; fixing UHID alone is not a DS3 wireless fix.
- BlueZ 5.83's cable-pairing approach illustrates a **per-device, USB-enrolled authorization** distinct from normal link-key bonding. **BlueZ is not Fluoride**; do not port a global L2CAP low-security setting or accept spoofed MACs based only on `sixpair`. Need design that verifies device enrollment/identity and avoids compromising all HID devices.

**B — Android Java HID Host admission, separately from native.**
- M3 actual `HidHostService.okToConnect()` in original Android Bluetooth APK at DEX `0x26e880` requires `BOND_BONDED == 12` plus connection policy UNKNOWN(-1) or ALLOWED(100). A cable-enrolled Sixaxis may have no traditional bond.
- On rejected initial connected event, `HidHostService$1.handleMessage` case 3 invokes `virtualUnPlugNative()` (not merely harmless disconnect); avoid unintended DS3 wireless master/address consequences.
- M3 TvSettings `BluetoothPairingRequest` passes `setPin(null)` for variant 0 and can reject PIN; exact active variant not proven.
- 2025 international OEM firmware was investigated and found not to fix the relevant Bluetooth APK/TvSettings implementation; do not recommend firmware flashing.

**C — Kernel UHID SET_REPORT response when wireless HID is finally allowed.**
- Linux `hid-sony` DS3 BT init sends Feature SET_REPORT F4 payload `F4 42 03 00 00` and may await matching `UHID_SET_REPORT_REPLY = 14`; missing completion risks kernel driver probe failure. AOSPs vary; use actual M3 original evidence below.
- At `0x1a692a–0x1a694c` original GET ingress increments per-device queue count `+0x2c`, allocates/stores original 32-bit UHID GET request ID from `[sp,#0x44]`, enqueues.
- At `0x1a7018` GET completion helper checks queue/fd, consumes original GET ID, constructs `UHID_GET_REPORT_REPLY = 10` (`0x1a709a`), writes through helper `0x1a5fb0`; ELF PLT `0x5dfe70` verified via `R_ARM_JUMP_SLOT` relocation at `0x5ff948` to libc `write` with `0x111c`-byte event and EINTR retry.
- Original SET ingress at `0x1a6964–0x1a6a26` (literal at `0x8c460` `UHID_SET_REPORT: Report type = %d, report_size = %d`) forwards report, **without analogous SET request ID enqueue** in observed path.
- Callee `0x1e15c8` allocates payload length+22, copies report, sets an **internal** BTA message field `0x000e` at buffer+4 and dispatches via `0x15d4b2` → `0x16b018`. **Do not confuse internal message 0x000e with UHID kernel event 14.** The wrapper at `0x15d4b2` includes internal event `0x1708`, command 5, subtype and payload pointer; no original UHID request ID.
- Native event dispatcher reads `w4_evt` (`[r4,#0x1c]` at `0x15ca54`); SET event 5 goes via `0x15ca94` to `0x1a6fec`, a **log-only callback** (exact unsupported text). A different GET event 4 branch at `0x15cb14` enters real GET helper `0x1a7018`. Upper callback at `0x15cb28`, then `0x15cb2c` clears `w4_evt` to zero.
- Thus source and binary independently establish **missing standard SET ID queue + no-op completion callback**, but exhaustive absence of every alternate UHID type-14 writer has NOT been proven and real DS3 runtime reachability untested.

## 5. Crucial transaction safety and model limitations

- M3 SET completion callback `bta_hh_co_set_rpt_rsp(dev_handle,status)` contains **no UHID request ID nor epoch**; `w4_evt=5` is an event class, not transaction identity.
- Never reply success simply because a report was enqueued or because `status=0` was guessed. Determine actual status to UHID errno mapping.
- Concurrent SETs on one device, timeout followed by subsequent SET, disconnect/reconnect, stale completion and unsolicited callback can cause mis-attribution.
- PR #50 offline Python `set_report_transactions.py` models **one in-flight SET per device** and permanently quarantines on timeout/disconnect within one manager; removed unsafe `reset_after_verified_new_session()`. Eight host unit tests passed. The model does **not** prove Fluoride ordering or handle late completion after a previous apparent success.
- A production solution must own request queue/lifetime, handle exact kernel reply ID, status, bounds, cancellation, generation/isolation and callback ordering, and verify AOSP source behavior before writing to UHID.

## 6. ARM32 build and replacement: explicit acceptance gates

The public H618 BSP is a promising source tree, not the exact Oranth OEM factory build. Compiling its default board target could give ARM64 or wrong target ABI. Before ever loading a build on M3:
1. Pin the matching BSP/AOSP revision and record Android version, build flags (`OS_ANDROID`, `ENABLE_UHID_SET_REPORT`), compiler, Soong target, 32/64-bit product config.
2. Build **Android 12 ARM32 libbluetooth.so** offline, record SHA and build provenance; compare with original ELF `readelf -h/-d/-Ws/-r` for `ELFCLASS32`, ARM, SONAME, NEEDED libraries, exported symbols, undefined imports, PLT/linker namespaces and actual mapped dependencies. Size/hash equality not expected unless exact OEM source/toolchain.
3. Check `libbluetooth_jni.so` and Bluetooth APK behavior; a native `.so` does **not** bypass Java bond policy.
4. Validate correct per-device DS3-specific auth policy on host synthetic tests, without weakening other devices. Record risks and rollback before any live test.
5. Only after demonstrated recovery/AVB/system-partition feasibility **and separate explicit Owner approval** contemplate a bounded M3 deployment. Never interpret an offline successful build as deployment approval.

## 7. First implementation milestones in this PR

- **S1 — Source provenance:** pin immutable BSP SHA, write table matching functions, enums, structs, defines to original M3 ELF and establish build prerequisites. Keep links to PR #50 primary raw findings.
- **S2 — Host/offline tests:** write source-level SET request ID correlation tests, plus failures/out-of-order callbacks; distinguish test proofs from real native guarantees.
- **S3 — Source patch:** add minimal SET_REPORT handling in source with bounded per-device state and correct response status; unit test, avoid global L2CAP security changes.
- **S4 — Auth design:** investigate source-level L2CAP policy for cable-enrolled DS3, and Java bond-gate options as separate patch proposals, with explicit threat model and no code deployment.
- **S5 — Reproducible ARM32 build:** record toolchain/product selection, compile offline, compare ABI against owner ELF, produce GO/NO_GO report. This step is exploratory, not an authorization for live testing.

## 8. Carry-forward instructions for a new chat

Repository `franfran/android-bt-gamepad`. Work exclusively on `feat/m3-ds3-source-first` and its Draft PR. Read **this document first**, `AGENTS.md`, linked PR #50 source-first feasibility/ELF technical evidence, and existing device/recovery handoffs. User is PM; use Cantonese/Traditional Chinese for reports. User has approved creating a new branch/PR and offline source-first work, **not** a live Bluetooth injection or system library replacement. Do not merge PR #50; it remains a separate research archive. Prioritize concrete source analysis/patches/build evidence and meaningful findings; avoid repeatedly asking for known USB/firmware facts. Maintain precise PROVEN vs HYPOTHESIS distinctions.
