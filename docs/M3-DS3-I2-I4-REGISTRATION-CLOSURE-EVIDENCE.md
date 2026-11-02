# I2/I4 registration closure and historical-evidence classification

Pinned BSP: `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. Research only.

## Verified registration edges (new)
- [bta/dm/bta_dm_act.cc#L235-L243](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/dm/bta_dm_act.cc#L235-L243) declares `bta_security.p_auth_complete_callback=&bta_dm_authentication_complete_cback`.
- [bta/dm/bta_dm_act.cc#L375-L385](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/dm/bta_dm_act.cc#L375-L385) **actually registers** the `bta_security` table through either shim `bluetooth::shim::BTM_SecRegister` or legacy `get_btm_client_interface().security.BTM_SecRegister` depending on source build/runtime configuration. This closes the earlier unresolved registration invocation within BTA.
- [bta/dm/bta_dm_act.cc#L253-L258](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/dm/bta_dm_act.cc#L253-L258) stores the higher BTA DM security callback; follow-up can identify its callsite if precise whole-chain initialization is required.
- [Bluetooth JNI hid_host.cpp#L181-L189](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L181-L189) builds native HID callback table, and [#L225-L236](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L225-L236) actually calls `sBluetoothHidInterface->init(&sBluetoothHidCallbacks)`. [btif/src/btif_hh.cc#L1220-L1229](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1220-L1229) stores the callback pointer. This closes the HID JNI/BTIF registration edge, but does **not** imply a supported third-party plugin registration surface.

## Existing PR #50 evidence: classification, not new telemetry
- [PR #50 feasibility](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-SOURCE-FIRST-FLUORIDE-BUILD-FEASIBILITY.md) explicitly records earlier HCI Authentication Requested followed by failure status `0x22`, before a demonstrable wireless UHID initialization.
- [PR #50 kernel UHID gate](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-KERNEL-UHID-SETREPORT-GATE.md) independently demonstrates a callback-level absence of standard UHID SET_REPLY logic in the original OEM ELF; **does not** prove a DS3 runtime session reached that code.
- JNI and native public BSP registrations are **source-proven**; that does not mean the complete observed M3 event sequence is captured or that the source exactly matches OEM binaries.
- Java incoming rejection is **source and prior OEM DEX corroborated**, but **not measured in the historic failed native connection attempt**.

## Scenario evidence grade
| Scenario | Direct M3 evidence | Pinned source support | Current conclusion |
| --- | --- | --- | --- |
| A: HCI authentication timeout 0x22 | Yes, prior historical capture summary | BTM timeout handling, BTA DM callback registration and BTIF failure mapping | **Observed symptom**, cause and exact callbacks unresolved |
| B: successful HID native OPEN then Java rejected unbonded DS3 | Not established | Java `okToConnect` + conditional virtual-unplug | **Possible future gate**, not proven triggered |
| C: successful admission then UHID SET_REPORT waiting | Not established on live DS3 | Original OEM ELF standard callback deficiency + pinned source | **Confirmed implementation gap**, runtime reachability unresolved |

## Architecture implication
Do not start writing the DS3 plugin/daemon based only on source-callgraph completion. Primary blocking evidence remains the HCI timeout (0x22); any architecture must preserve security, identify legitimate authorization, and show transport ownership. PR #51's UHID source patch remains separately useful but later-stage.

## Next offline work
Locate precise DM callback supplier and, where available, sanitized raw historical trace sections in PR #50. Define criteria to distinguish lost remote authentication response, local key mismatch, and Java rejection **without inventing a cause**. Any live M3 experiments need separate explicit Owner permission.

Safety: no system writes, no injection, no restart, no security flag weakening, no runtime tests. PR #52 stays Draft.
