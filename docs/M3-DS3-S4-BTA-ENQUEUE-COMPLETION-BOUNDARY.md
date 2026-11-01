# S4 source trace: API enqueue is not HID completion

2026-11-01. Static evidence from immutable BPI H618 Android12 BSP commit `250eabfc529518b7f26432663ed0a867ab2f625d`, `system/bt` tree `d6f07310f73694977b301eac63d67b219ca20625`.

## Newly verified queue boundary

- [`bta/hh/bta_hh_api.cc:136-151`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_api.cc#L136-L151): `bta_hh_snd_write_dev` allocates `tBTA_HH_CMD_DATA`, fills `BTA_HH_API_WRITE_DEV_EVT`, handle, transaction type/report fields, then calls **`bta_sys_sendmsg(p_buf)`**. The message format has no UHID request ID, producer origin, or generation. Enqueueing is not a Bluetooth handshake.
- [`bta/hh/bta_hh_api.cc:166-169`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_api.cc#L166-L169): `BTA_HhSetReport` wraps this path for `HID_TRANS_SET_REPORT`. It returns `void`; the caller has no transaction token or synchronous dispatch outcome.
- [`stack/hid/hidh_api.cc:413-438`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_api.cc#L413-L438): `HID_HostWriteDev` checks registration, handle range/in-use and connected state; failure releases the outgoing `pbuf` and returns an error. Success delegates to `hidh_conn_snd_data`. **Success means local dispatch was accepted**, not remote SET handshake acknowledgement.
- [`bta/hh/bta_hh_act.cc:1015-1058`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L1015-L1058): BTA invokes HID send; on local failure emits an application callback directly, with no UHID SET callout. After successful send, selected operations overwrite the shared `w4_evt` without checking an outstanding operation at that location.
- [`stack/hid/hidh_conn.cc:678-682`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L678-L682): incoming HID handshake reports handle and parameter, not request ID.
- [`bta/hh/bta_hh_act.cc:635-674`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L635-L674): BTA interprets handshake with current `w4_evt` and dispatches SET callout, which in this source [only logs unsupported reply](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L566-L568).

## Consequence for a source patch

A compatible design must preserve **three distinct milestones**: (1) request received and authorized; (2) local BTA/HID dispatch accepted or rejected; (3) actual remote HID handshake received and correctly correlated. `bta_sys_sendmsg`, `HID_HostWriteDev == HID_SUCCESS`, and `BTA_HH_SET_RPT_EVT` each prove different things and are *not* equivalent to a safe UHID kernel ACK.

**Immediate next source work:** map the native `tBTA_HH_CMD_DATA` structure definition and `bta_sys_sendmsg` lifetime, trace `hidh_conn_snd_data` and command interleavings, and design an explicit per-handle origin/token propagation scheme that survives local send errors and disconnects. Do **not** alter native ABI by casually appending fields to shared structs or assume the BSP is OEM ABI-equivalent.

**Blocker:** without proof of token-to-handshake mapping, no source-level `UHID_SET_REPORT_REPLY` should be emitted on observed SET completion. Auth 0x22 and OEM Java bond/virtual-unplug gate remain independent. No ARM32 build or M3 access performed.
