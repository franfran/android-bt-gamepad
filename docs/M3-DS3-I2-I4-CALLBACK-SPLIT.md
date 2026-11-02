# I2/I4 — BTM/BTA/BTIF authentication and HID event split

Source pin: BPI-SINOVOIP/BPI-H618-Android12 `250eabfc529518b7f26432663ed0a867ab2f625d`. Research-only. No live HCI/event trace replay, and no inference of actual callback scheduling on M3.

## A. Authentication / bonding path
- [stack/btm/btm_sec.cc#L3043-L3070](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L3043-L3070): `btm_sec_auth_complete(handle, status)` handles authentication completion and retry/collision logic.
- [bta/dm/bta_dm_act.cc#L2111-L2139](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/dm/bta_dm_act.cc#L2111-L2139): `bta_dm_authentication_complete_cback` packages unsuccessful reason as `auth_cmpl.fail_reason`, issues `BTA_DM_AUTH_CMPL_EVT` to registered security callback.
- [btif/src/btif_dm.cc#L1520-L1527](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_dm.cc#L1520-L1527): BTIF dispatcher routes `BTA_DM_AUTH_CMPL_EVT` to `btif_dm_auth_cmpl_evt`.
- [btif/src/btif_dm.cc#L1029-L1044](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_dm.cc#L1029-L1044): timeout `HCI_ERR_LMP_RESPONSE_TIMEOUT = 0x22` is distinct from explicit auth fail 0x05. Existing interop retry requires pairing conditions and does not authenticate a peer.
- **LIMITATION:** these functions show a *possible source chain*, not proof every observed 0x22 on M3 emitted a Java bond callback. For BTM → BTA registration, trace specific callback assignment and route in a follow-up.

## B. HID Host connection path
- [bta/hh/bta_hh_act.cc#L775-L793](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L775-L793): `bta_hh_open_failure` maps `HID_ERR_AUTH_FAILED` to `BTA_HH_ERR_AUTH_FAILED`, otherwise generic `BTA_HH_ERR`, emits `BTA_HH_OPEN_EVT`, and clears `w4_evt`.
- [bta/hh/bta_hh_act.cc#L840-L859](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L840-L859) contains analogous outgoing HID connection-failure handling. Not every timeout necessarily maps to `HID_ERR_AUTH_FAILED`.
- [btif/src/btif_hh.cc#L772-L831](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L772-L831): `BTA_HH_OPEN_EVT` on success proceeds toward descriptor/UHID and HAL connected event; on failure calls `btif_dm_hh_open_failed`, destroys available UHID fd, and emits `BTHH_CONN_STATE_DISCONNECTED`.
- [btif/src/btif_hh.cc#L1105-L1135](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1105-L1135): `bte_hh_evt` transfers BTA HID events onto BTIF context.
- **LIMITATION:** a failed HID open does not by itself prove Java `okToConnect()` was evaluated; the Java rejection gate specifically requires an incoming `CONNECTED` state from previously disconnected state.

## C. Java gate (from previous I4 investigation)
- [HidHostService.java#L185-L206](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L185-L206): only the relevant newly connected incoming transition with `!okToConnect` invokes `virtualUnPlugNative`.
- [HidHostService.java#L892-L919](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L892-L919): quiet mode, bond state, and connection policy checks.

## Architecture consequence
A minimal DS3 adapter must solve authentication/transport and Java admission separately; it cannot claim Java rejection causes the earlier native 0x22 without showing a real event sequence. Conversely, improving Java alone will not make failed native L2CAP authentication succeed. Source paths do not authorize globally relaxing HID security or fabricating bond/link-key state.

## Next offline gates
1. Trace registered BTM security callback to BTA, and native/HAL to Java callback registration to complete the chain.
2. Build a sanitized event-order matrix for: (a) native 0x22 before HID OPEN, (b) success to Java CONNECTED but not bonded, (c) successful admission but UHID feature SET_REPORT not replied.
3. Only after identities, ordering and permissible per-device policy are resolved, compare minimal in-stack adapter with PR #51. No M3 runtime operations or security changes.
