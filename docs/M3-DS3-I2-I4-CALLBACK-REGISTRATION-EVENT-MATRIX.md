# I2/I4 — Callback registration and event-order evidence matrix

Pinned source: `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. Static analysis only, not a captured M3 sequence.

## Registered interfaces verified

**Security callbacks:** [bta/dm/bta_dm_act.cc#L235-L243](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/dm/bta_dm_act.cc#L235-L243) defines `bta_security` with `p_auth_complete_callback = &bta_dm_authentication_complete_cback`. [#L253-L258](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/dm/bta_dm_act.cc#L253-L258) stores the higher-level BTA DM callback via `bta_dm_enable(p_sec_cback)`. [#L2118-L2139](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/dm/bta_dm_act.cc#L2118-L2139) sends `BTA_DM_AUTH_CMPL_EVT` on unsuccessful authentication. [btif/src/btif_dm.cc#L1524-L1525](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_dm.cc#L1524-L1525) dispatches to `btif_dm_auth_cmpl_evt()`. **Remaining link to validate:** the exact BTM registration invocation and BTA-DM caller configuration, not merely presence of registration records.

**HID host to Java:** [btif/src/btif_hh.cc#L1105-L1135](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1105-L1135) transfers HID events into BTIF; [#L772-L831](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L772-L831) invokes `HAL_CBACK(bt_hh_callbacks, connection_state_cb,...)` as connected or disconnected depending on HID open outcome. [Bluetooth JNI com_android_bluetooth_hid_host.cpp#L54-L70](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L54-L70) forwards via `CallVoidMethod(... method_onConnectStateChanged ...)`; [#L181-L199](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L181-L199) registers the callback table and Java method ID. [Java HidHostService.java#L802-L807](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L802-L807) queues `MESSAGE_CONNECT_STATE_CHANGED`, then [#L185-L206](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L185-L206) conditionally evaluates `okToConnect()` and invokes virtual-unplug on rejected *newly connected* transition.

## Distinguish these diagnostic event sequences
| Scenario | Expected events conditional on specific path | What cannot be inferred |
| --- | --- | --- |
| A: HCI authentication complete returns 0x22 | BTM timeout handling; potentially BTA DM auth completion → BTIF DM failure and HID open failure → BTIF HID disconnected | Exact ordering, whether every callback occurs, Java CONNECTED admission, actual root cause |
| B: Native HID opens but Java bond=NONE | BTIF HID connected → JNI `onConnectStateChanged` → Java handler `okToConnect=false` → `virtualUnPlugNative` | That B ever occurred on M3 or that it preceded 0x22 |
| C: Java admits connection but kernel hid-sony SET_REPORT does not complete | UHID feature SET ingress; missing reply possible; probe/input failure | That C is reached in current M3 0x22 capture, or which UHID completion has valid unique ownership |

## Proposed evidence schema (sanitized, monotonic)
`{run_id, monotonic_ms, layer, event, status_hex, direction, hid_handle_or_ephemeral_id, source, evidence_grade}`.
Never expose link keys, device MAC, private logs, home IP, raw proprietary dumps. If timestamps are from distinct clocks or old captures without monotonic origin, **do not compare as if synchronized**.

## Current architectural conclusion
No evidence that a drop-in plugin solves either source path. A minimal source adapter remains the most plausible **investigation direction**, but there is no implementation GO. Must determine actual auth-timeout root cause, trusted per-device authorization and Java admission without forged bond state. Keep controller-ownership question open for standalone daemon.

## Next
1. Locate explicit `BTM_SecRegister(&bta_security)` (or equivalent) and `bta_dm_enable` call graph.
2. Locate JNI HID callback-table init `init(&sBluetoothHidCallbacks)` and connect state handling in OEM and source; build a no-code host event-sequence checker.
3. Review PR #50 historical capture for complete 0x22 event timeline without acquiring new device data.
Research only. No runtime operations/patch deployments.
