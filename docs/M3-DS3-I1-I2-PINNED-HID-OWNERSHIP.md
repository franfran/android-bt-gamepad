# I1 / I2 — pinned H618 source: HID Host dispatch and Classic HID ownership

Date: 2026-11-01 (America/Toronto). **Read-only source evidence.** This is not a completed exhaustive extension surface or security assessment.

## Source provenance
BPI-SINOVOIP/BPI-H618-Android12 pinned commit `250eabfc529518b7f26432663ed0a867ab2f625d`; system/bt tree `d6f07310f73694977b301eac63d67b219ca20625`. Matching public BSP source is not proof of identical OEM build or ABI.

## VERIFIED source observations

### 1. Static HID Host interface dispatch (I1)
- [btif/src/bluetooth.cc lines ~420-448](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/bluetooth.cc#L420-L448): `static const void* get_profile_interface(const char* profile_id)` compares known profile IDs. Its `BT_PROFILE_HIDHOST_ID` branch directly returns `btif_hh_get_interface()`. The selector is placed in Bluetooth HAL interface near line 607.
- This is **built-in static profile selection**, not registration of an arbitrary shared library. No `dlopen` or external `register_profile` was found in **this inspected file**. A tree-wide negative claim is not established.

### 2. Internal HID Host service lifetime (I1/I2)
- [btif/src/btif_hh.cc lines ~667-690](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L667-L690): `btif_hh_service_registration(bool enable)` uses `BTA_HhEnable(bte_hh_evt)` / `BTA_HhDisable()`. This is a built-in service lifecycle switch, **not proof of runtime pluggability**.
- [btif/src/btif_hh.cc lines ~590-600](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L590-L600) invokes `BTA_HhOpen(*bd_addr)` for outgoing HID Host connection; upstream event dispatcher owns success/failure state.

### 3. L2CAP HID PSM registration and security (I2)
- [stack/hid/hidh_conn.cc lines ~105-118](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L105-L118): `L2CA_Register2(HID_PSM_CONTROL,..., BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT)`; same for `HID_PSM_INTERRUPT`. Failure registering second PSM deregisters the first.
- [stack/hid/hidh_conn.cc lines ~431-443](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L431-L443) and [~860-877](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L860-L877): outbound interrupt/control `L2CA_ConnectReq2` likewise uses authentication and encryption.
- [stack/hid/hidh_conn.cc ~907-913](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L907-L913): `hidh_conn_dereg()` calls `L2CA_Deregister` for both PSMs.

## Interpretations and limits
- **PROVEN:** This pinned source has a prewired HID Host interface, internal BTA HID Host service lifecycle, and L2CAP registration using authenticated+encrypted Classic HID PSMs.
- **INFERRED:** A parallel independent daemon sharing the same active controller/PSMs is unlikely to work without an explicit coexistence or hand-off mechanism. These source reads alone do not establish whether Android exposes an acceptable per-device L2CAP socket path or controller ownership delegation to another process.
- **UNTESTED:** OEM-vs-BSP identity, HID profile vendor hooks elsewhere in the tree, Java/system API escape hatch, independent daemon transport ownership, specific per-device DS3 security compatibility, actual on-device input injection.

## Architectural implications
1. **Candidate A (pure drop-in .so)**: NO_GO for the *assumption* that `get_profile_interface` is a third-party plugin registry. Do not declare all extension points absent yet.
2. **Candidate B (separate daemon)**: conditional; must explain how the daemon obtains legitimate controller/PSM ownership *while the native stack stays available for other hardware*. No unsafe controller takeover experiments.
3. **Candidate C (minimal adapter)**: strongest current research candidate for preserving existing transport ownership, but may still require coordinated native/Java changes and build validation. Do not call it runtime-ready.
4. **Candidate D (supported configuration)**: still open; inspect vendor interop, properties and per-device policy behavior. No global security downgrade.

## Next offline inspections
- Trace `stack/hid` registration initiation, security check path and per-device interop hooks; enumerate source files and precise source commits.
- Inspect `btif/src/btif_dm.cc`, `device/src/interop.cc`, and relevant JNI/Java registration for any **supported** per-device exception.
- Compare possible delegation paths with Linux Bluetooth sockets, but document that generic Linux socket support does **not** prove it is exposed on the M3 Android Bluetooth stack.
- Assess Java `HidHostService.okToConnect()` separate bond gate and virtual-unplug.
- Produce a bounded architecture decision, preferably with a no-code proof-of-concept contract.

## Safety
No M3 probes or writes, injection, Bluetooth service restart, new daemon execution, library/APK swap, key manipulation, global security relaxation, or merge. Research Draft PR #52 stays independent of PR #50 and #51.
