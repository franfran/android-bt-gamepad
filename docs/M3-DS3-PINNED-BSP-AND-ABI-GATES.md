# M3 DS3 — pinned Fluoride source and offline compatibility gates

Status: **SOURCE ATTRIBUTION ONLY; NO DEVICE DEPLOYMENT** (2026-11-01).
This document supplements [source-first handoff](M3-DS3-SOURCE-FIRST-HANDOFF.md) and references independent [PR #50](https://github.com/franfran/android-bt-gamepad/pull/50). Do not merge #50.

## Immutable provenance

- Upstream: `https://github.com/BPI-SINOVOIP/BPI-H618-Android12`
- Observed upstream `master` commit SHA: `250eabfc529518b7f26432663ed0a867ab2f625d` (2026-10-19).
- **Upstream `system/bt` tree SHA:** `d6f07310f73694977b301eac63d67b219ca20625`.
- Pinned source: `https://github.com/BPI-SINOVOIP/BPI-H618-Android12/tree/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt`
- Upstream blob SHA identifiers:
  - `btif/co/bta_hh_co.cc`: `c5aba4425d272dc963b6f60567d7b79fb0c18f75`
  - `bta/hh/bta_hh_act.cc`: `bc092b68c12502d2f73a7dbab65426ab05fd28c1`
  - `stack/hid/hidh_conn.cc`: `87ded1c07670aec120017f54f17bccc59fe2cdb9`
- Original **installed** 2024 M3 `/system/lib/libbluetooth.so` (private; never commit):
  SHA256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`, build ID `0d29a62178e43066e018216c1f1d5b18`; ELF32 ARM / Android 12 API 31.
- This source snapshot is **not proven** to be the OEM's exact source revision, flags, toolchain or vendor ABI. Do not use it as a replacement merely on the basis of similar functions.

## Pinned source ↔ original M3 binary crosswalk

| Pinned public source | Public behavior | Independently observed original M3 evidence | Conclusion |
|---|---|---|---|
| `btif/co/bta_hh_co.cc:153-159` | GET queues `ev.u.feature.id` in `get_rpt_id_queue` | Thumb GET ingress `0x1a692a–0x1a694c` stores 32-bit UHID GET ID | Strong functional correspondence |
| `btif/co/bta_hh_co.cc:165-189` | `#ifdef OS_ANDROID` SET event sends report through `btif_hh_setreport`, no matching SET ID enqueue | SET ingress `0x1a6964–0x1a6a26`; same log literal `UHID_SET_REPORT: Report type...` | Strong functional correspondence; `OS_ANDROID` path likely compiled |
| `btif/co/bta_hh_co.cc:566-568` | `bta_hh_co_set_rpt_rsp` only logs `UHID_SET_REPORT_REPLY not supported` | `0x1a6fec` log-only callback, identical text | Strong functional correspondence; normal callback does not complete SET |
| `bta/hh/bta_hh_act.cc:662-674` | SET handshake invokes co callback then upper callback then clears `w4_evt` | `0x15ca94` / `0x15cb2c` event-5 dispatch and clear | Corresponding flow; not transaction-ID aware |
| `stack/hid/hidh_conn.cc:107-115` | `L2CA_Register2` HID control and interrupt with `BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT` | Original registers PSM `0x11` and `0x13`, mask `0x36`; security call `0x2897b4` | Global auth constraint; **do not disable** |
| `main/Android.bp:68+` | Soong `cc_library_shared` named `libbluetooth` | Original shared ELF32 ARM | Build entry point, NOT ABI compatibility proof |

Original ELF offsets/VMAs above apply **only to the hash-pinned 2024 file**, not a live ASLR process, newer firmware, or compiled BSP binary. Thumb function pointer low bit is ISA state, not instruction address. See PR #50 for original disassembly and uncertainty.

### Additional source-level hazards

1. `bta_hh_co_set_rpt_rsp(dev_handle,status)` has no UHID ID, generation, epoch or transaction token. An ordinary FIFO completion assumption is unsafe under timeout, disconnect, unsolicited or reordered callbacks. Neither `w4_evt=5` nor internal BTA `0x000e` is UHID kernel event type 14.
2. Current `bta_hh_co.cc:425-427` flushes GET ID queues in a loop over **all devices** during close; any new per-device SET queue needs a strictly scoped lifecycle and must not repeat this behavior.
3. Existing GET queue uses `fixed_queue_new(SIZE_MAX)`; do not reuse an unbounded queue for SET requests.
4. Linux UHID SET reply requires exact request ID and status. Success only after the corresponding actual HID handshake; failure is not a successful probe. Determine BTA status → Linux UHID error mapping, including failure and cancelled transaction.
5. OS_ANDROID and other Soong flags must be validated **in the actual ARM32 build**, not deduced solely from the presence of a preprocessor branch.

## Three independent blockers, and safe patch direction

**A. Native L2CAP/HCI authentication (earliest measured failure):** Original M3 saw Authentication Requested `0x0411` and HCI failure `0x22` *before* UHID. Public source registers both HID PSMs with authentication/encryption. Never relax `L2CA_Register2` or `L2CA_ConnectReq2` globally. A future DS3-specific cable-enrollment policy must have trusted, persistent, non-MAC-only enrollment evidence; account for MAC spoofing and controller impersonation. USB sixpair alone sets a master address and does not establish a shared cryptographic secret or authenticated identity. **No approved secure exception design yet**.

**B. Java HID Host:** Original OEM APK's `HidHostService.okToConnect` requires `BOND_BONDED=12` and acceptable connection policy. Initial reject may call `virtualUnPlugNative()`. A native-only `.so` patch cannot pass this separate check. A future scoped Java design must avoid global acceptance of unknown HID devices and avoid destructive virtual unplug. **No OEM APK change authorized.**

**C. Kernel UHID SET_REPORT:** Kernel `hid-sony` Bluetooth path requires an F4 Feature SET and a matching `UHID_SET_REPORT_REPLY`. A production patch needs original kernel ID retention, response ordering, device/session lifetime, bounds, timeout/quarantine, and status correctness. The host-only PR #50 Python model is not an execution proof. **Do not add unconditional ACK or inject F4 separately.**

## ARM32 build and verification contract (offline only)

Source checkout, after obtaining the BSP through normal offline clone:

```sh
git clone https://github.com/BPI-SINOVOIP/BPI-H618-Android12.git
cd BPI-H618-Android12
git checkout --detach 250eabfc529518b7f26432663ed0a867ab2f625d
test "$(git rev-parse HEAD)" = 250eabfc529518b7f26432663ed0a867ab2f625d
test "$(git rev-parse HEAD:system/bt)" = d6f07310f73694977b301eac63d67b219ca20625
```

Note: full Android Soong product builds require the matching BSP checkout, Android prebuilts, Soong dependencies, sufficient storage and target configuration. An isolated NDK `clang -shared` test does **not** establish an OEM-compatible Fluoride `libbluetooth.so`.

Required build evidence before PASS:
- Record `source build/envsetup.sh`, exact `lunch` product/variant, Soong command, actual build logs, pinned toolchain, `TARGET_ARCH=arm` / `TARGET_ARCH_VARIANT` / `TARGET_2ND_ARCH`, `OS_ANDROID`, compiled source paths and module source selection.
- Compile `libbluetooth` for **32-bit ARM** specifically. Never infer ABI from default H618 ARM64 lunch target or from `m libbluetooth` succeeding on another architecture.
- Compare `readelf -h -d -Ws -r -n` for built and private original; check ELFCLASS32, e_machine ARM, Android ABI/API, SONAME, DT_NEEDED, imported/exported symbol names and versions, PLT relocations, and original M3 `libbluetooth_jni.so` import compatibility.
- Account for Android linker namespaces, actual mapped APEX/system dependencies and OEM compiler/C++ ABI differences. The original and new binaries are not expected to have equal size/hash.
- Offline unit tests must exercise normal SET, negative handshake, duplicate/unsolicited response, concurrent SET, timeout, late response, disconnect/reconnect and different device handle. **Do not return success on ambiguous callback**.
- Produce explicit `GO/NO_GO` report. Until compiled artifacts **and** compatibility evidence exist, build status = **NOT RUN**, deployment status = **NO_GO**.

## Current evidence boundary

- **Verified**: specific public upstream commit/tree/blobs, source lines above, existing PR #50 original native evidence and separate OEM Java gate.
- **Not verified**: full BSP toolchain build, OEM equivalent `libbluetooth.so`, precise C++ structs/layout, Java integration behavior under patched native, safe DS3-specific authorization, runtime UHID correlation.
- **Prohibited without separate owner approval**: touching M3, injections, flashing, swapping `libbluetooth.so` or APK, restarting Bluetooth, weakening global security, merging either Draft PR.
