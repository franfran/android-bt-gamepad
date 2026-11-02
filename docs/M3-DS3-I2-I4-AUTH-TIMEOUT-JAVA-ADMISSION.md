# I2/I4 — HCI 0x22 and Java HID Host admission: pinned source crosswalk

Source: BPI-SINOVOIP/BPI-H618-Android12 commit `250eabfc529518b7f26432663ed0a867ab2f625d`. **Source-only investigation; hardware behavior still unverified.** Keep separate from PR #51 patch/build work.

## Critical correction: 0x22 is a timeout reason, not HCI Authentication Failure (0x05)
Historical M3 evidence captured `HCI Authentication Requested (0x0411)` followed by **status 0x22**, whose HCI symbolic code is `HCI_ERR_LMP_RESPONSE_TIMEOUT`. This describes a timeout during the authentication sequence, **not** a controller response explicitly reporting `HCI_ERR_AUTH_FAILURE` (0x05). In PR #50/#51 short summaries the informal phrase 'authentication failure 0x22' means *authentication attempt failed with 0x22 timeout*, and must not be conflated with status 0x05.

[Pinned stack/btm/btm_sec.cc lines 3043–3070](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L3043-L3070): `btm_sec_auth_complete(handle,status)` handles authentication completion and retries/collisions. [Lines 3574–3579](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L3574-L3579): LMP response timeout maps to `BTM_DEVICE_TIMEOUT`, while other failure statuses map to `BTM_ERR_PROCESSING`. These are **downstream consequences**, not evidence of the timeout's root cause. Possible missing key/legacy behavior/controller response etc. must not be asserted without precise HCI sequence.

[Pinned btif/src/btif_dm.cc lines 1029–1044](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_dm.cc#L1029-L1044): `HCI_ERR_LMP_RESPONSE_TIMEOUT` belongs to timeout/retry branch and can use existing `INTEROP_AUTO_RETRY_PAIRING` if its pairing context permits. This does *not* authorize the peer, provide a missing link key, or guarantee a remedy. [Lines 1056–1069](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_dm.cc#L1056-L1069) separately classify HCI 0x05 `HCI_ERR_AUTH_FAILURE` and missing key. These reasons should remain distinct.

## Java policy: separately proven in the same pinned public BSP
[Pinned packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java lines 892–919](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L892-L919):
- `okToConnect(device)` rejects when AdapterService absent, quiet mode enabled without target, bond state is not `BluetoothDevice.BOND_BONDED`, or policy neither `UNKNOWN` nor `ALLOWED`.
- A merely cable-enrolled DS3 is **not proven bonded** by changing its master address.
- [Lines 185–206](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L185-L206): incoming `CONN_STATE_CONNECTED` from a previously disconnected state rejected by `okToConnect` invokes `virtualUnPlugNative`. It is **not** an all-events general-case rule and should not be described as every rejected connection.
- Independent PR #50 reverse engineering previously identified the same Java policy in OEM APK, strengthening crosswalk but not confirming every OEM callback branch matches.

## Implications
1. The native timeout `0x22` is observed **before** a successful HID path. An interop retry flag alone is not demonstrated to solve it; root cause remains unknown.
2. The Android Java bond gate is a **separate later gate**. Even if a native adapter fixes Classic transport, it will still reject nonbonded inbound devices without a carefully designed trusted enrollment/bond solution.
3. Never synthesize a link key, fake bonded state, rewrite security flags globally, or suppress virtual-unplug without a full authorized device lifecycle model.
4. A 'plugin' that only forwards UHID reports cannot bypass A and B; a separate daemon still needs verified legitimate L2CAP ownership and security.

## Decision table (not a final architectural GO)
| Candidate | Evidence | Status |
| --- | --- | --- |
| Drop-in `.so` extension | Built-in static HID Host dispatch; no supported plugin registration shown in inspected files | Unproven / no interface demonstrated |
| Per-device interop flag | Existing timeout retry and pairing workarounds, no current DS3 auth exception | Insufficient alone |
| Independent daemon | Original stack owns HID PSM and security; controller hand-off unresolved | CONDITIONAL research only |
| Minimal Fluoride adapter | Source integration can address security admission + Java + UHID at explicit boundaries | Preferred investigation, **not runtime ready** |

## Suggested next offline tests
- Construct a **sanitized event timeline** differentiating HCI command status, HCI authentication complete status 0x22, bond state, HID open, and virtual-unplug; preserve timestamps and event origin. No new live capture required in this milestone.
- Locate precise `BTM_DEVICE_TIMEOUT` callback-to-BTA-HID propagation path and JNI callback order.
- Trace OEM-vs-pinned Java service differences if decompiled OEM evidence is available; do not claim Java patch alone addresses native timeout.
- Specify deterministic negative host tests: controller authentication stalls, state remains non-bonded, duplicate/unrelated callback, disconnection.

## Safety
Research only. No M3 process actions, `/system` or bond database writes, security relaxation, Bluetooth restart, injection, firmware operations or merge.
