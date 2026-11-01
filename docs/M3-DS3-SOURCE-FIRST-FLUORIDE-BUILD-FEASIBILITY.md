# Source-first implementation feasibility: public H618 Android 12 Fluoride

**2026-11-01 · Offline research · Supersedes blind reverse engineering as the primary development strategy.** This is source attribution/architecture planning, NOT approval to replace or flash the M3 library.

## Major discovery: exact strings and behavior in public C/C++ source

- Public **Banana Pi H618 Android 12 full BSP**: https://github.com/BPI-SINOVOIP/BPI-H618-Android12
- Direct source: https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/master/system/bt/btif/co/bta_hh_co.cc
- Legacy AOSP counterpart: https://android.googlesource.com/platform/system/bt/+/54a50f50ca583146cd2556950177678d906e1391/btif/co/bta_hh_co.cc

Direct GitHub file inspection of the H618 BSP confirms:
1. `btif/co/bta_hh_co.cc` around line 165 handles `UHID_SET_REPORT`, forwards Feature/Output/Input reports via `btif_hh_setreport`, but does **not** enqueue `ev.u.set_report.id`; adjacent `UHID_FEATURE` (GET) branch enqueues `ev.u.feature.id` into `get_rpt_id_queue`.
2. The same file around line 564 defines `bta_hh_co_set_rpt_rsp(uint8_t dev_handle, uint8_t status)` with the **exact log message** `%s: Error: UHID_SET_REPORT_REPLY not supported`. This closely matches original owner M3 ELF literal, Thumb log-only stub at `0x1a6fec`, actual callback dispatch and missing SET request queue.
3. `system/bt/bta/hh/bta_hh_act.cc` contains SET event completion and `p_cb->w4_evt = 0`; exactly the behavior previously corroborated in original M3 Thumb dispatcher `0x15cb2c`.
4. `system/bt/stack/hid/hidh_conn.cc` registers Classic HID Control/Interrupt PSMs with `L2CA_Register2` and `BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT`. These are **global profile security requirements**, so changing the registration itself is NOT an acceptable DS3-only shortcut.
5. `system/bt/main/Android.bp` explicitly builds a `cc_library_shared` named `libbluetooth` with `libbtif`, `libbt-bta`, `libbt-stack`, etc. This supplies a real source-level compilation starting point.

**Source confidence:** exceptionally high for **functional ancestry of the UHID section** (exact string and paired GET/SET paths). **Not yet demonstrated:** exact vendor commit lineage, identical compilation flags, native binary equivalence, ABI compatibility, full Bluetooth controller/transport integration, or equivalence of the rest of M3 native stack. H618 hardware similarity does NOT imply drop-in `.so` compatibility.

## Critical distinction: can compile vs can deploy

**In principle YES:** source-modify `btif/co/bta_hh_co.cc` and build an ARM32 `libbluetooth.so` in a matching Android tree. **Not yet ready:** existing Oranth M3 firmware is Android 12 / 32-bit Bluetooth process; using the Banana Pi default board product may produce a 64-bit library or link against different `libbluetooth_jni.so`/AIDL/HAL, shared libraries, Android platform symbols, and compile flags.

The owner-original installed `/system/lib/libbluetooth.so` is ELF32 ARM, SHA256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`, build-ID `0d29a62178e43066e018216c1f1d5b18`. A vendor-compatible rebuild must pass at minimum:
- Identify source revision/branch provenance versus actual ELF and 2024 build fingerprints.
- Build for **ARM32, Android API 31** in an appropriate source tree with matching compiler flags/target, **not the board's default ARM64 configuration by assumption**.
- Offline check ELFCLASS32, ARM EABI, `DT_NEEDED`, `SONAME`, exported symbol set/versions and required imported symbols against M3's actual JNI/native dependency map; evaluate C++ ABI and private structure/layout changes.
- Confirm compiled code includes correct **UHID SET queue + completion** and preserves original behavior for all other HID controllers; handle timeout, status, disconnect and stale callbacks; kernel `CONFIG_UHID=y`, `CONFIG_HID_SONY=y` already proven.
- Treat native SET_REPORT fix as **one of several gates**. It does not fix observed earlier HCI Authentication Requested failure `0x22` or OEM Java HID `BOND_BONDED` / possible virtual-unplug policy.
- No new native library may be run in live Bluetooth process until independently verified signature/partition/AVB/rollback, service restart safety, USB ADB recovery and explicit scoped Owner approval. A compiled `.so` is **not** a verified replacement.

## Source-first development tracks

**Track A (now, offline):** pin a public H618 BSP Git commit and AOSP Fluoride revision, trace original exact-function source for `bta_hh_co_set_rpt_rsp`, SET ingress, GET queue and `w4_evt`; establish source/ELF symbol+string correspondence. Prefer editing C++ code and building host-only unit tests over more unrelated Thumb reverse engineering.

**Track B (source-level prototype):** implement the missing SET-report request-ID queue, report status and matching kernel event reply in the source branch, with strict rejection of stale/concurrent requests and error mapping. Newer upstream Bluetooth provides a guarded `ENABLE_UHID_SET_REPORT` implementation for design reference; backport only reviewed portions compatible with M3-era structures, do not blindly cherry-pick recent source.

**Track C (separate DS3 auth):** use source to locate the Classic L2CAP incoming security decision already grounded by S8, design an **enrolled per-device** policy without global `BTA_SEC_AUTHENTICATE|BTA_SEC_ENCRYPT` changes or counterfeit bonding. Investigate Java Host integration via source separately; source access cannot override the M3 APK's actual bond gate.

**Track D (offline ARM32 reproducible build):** compile, test, compare public BSP output to the exact original ELF imports/exports/ABI. Any deployment remains NO_GO pending verified recovery and a separate Owner go-ahead.

## Suggested initial GO/NO_GO deliverable

- **GO** to pin public source commit, write a narrowly scoped source patch for UHID SET reply and host tests, try an **offline** ARM32 build.
- **NO_GO** to claim the public BSP is byte-identical with Oranth firmware; to install an ARM64 build in ARM32 process; to loosen global Bluetooth HID security; to sidestep Java bond checks; or to live inject/replace `/system/lib/libbluetooth.so`.

Reference files: `docs/M3-DS3-KERNEL-UHID-SETREPORT-GATE.md`, `docs/M3-DS3-S7-S8-INTEGRATION-CONTRACT.md`, `docs/S7-C4C-HANDOVER.md`, PR #49.
