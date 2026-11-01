# S4: HID send ownership and failure-path matrix (pinned source)

Date: 2026-11-01. Offline static evidence only. Source pin: `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`, `system/bt` tree `d6f07310f73694977b301eac63d67b219ca20625`.

## Exact evidence

- [`bta/hh/bta_hh_int.h:77-85`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_int.h#L77-L85): `tBTA_HH_CMD_DATA` owns `BT_HDR_RIGID hdr`, `t_type`, `param`, `rpt_id`, `data`, and `BT_HDR* p_data`. No UHID ID, origin or generation; `rpt_id` is a HID report ID, **not** a UHID transaction ID.
- [`bta/hh/bta_hh_api.cc:136-150`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_api.cc#L136-L150): API allocates command, transfers pointer in message to `bta_sys_sendmsg`. Do not infer delivery/remote acknowledgement from this enqueue.
- [`bta/hh/bta_hh_main.cc:223-245`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_main.cc#L223-L245): BTA invalid-handle path frees `p_data`, emits `BTA_HH_ERR_HDL` via callback for SET; it does NOT go through `bta_hh_co_set_rpt_rsp`.
- [`stack/hid/hidh_api.cc:413-438`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_api.cc#L413-L438): `HID_HostWriteDev` validates register, in-use and connected; frees `pbuf` upon rejection, otherwise delegates to transport.
- [`stack/hid/hidh_conn.cc:728-770`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L728-L770): `hidh_conn_snd_data` returns `HID_ERR_NO_CONNECTION` if ACL down; `HID_ERR_CONGESTED` if congested; chooses L2CAP control channel for GET/SET and interrupt for DATA. Caller must not assume accepted-on-wire means acknowledged.
- [`stack/hid/hidh_conn.cc:824-827`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L824-L827): `L2CA_DataWrite` failure/congestion returns HID error; this is not remote handshake.
- [`bta/hh/bta_hh_act.cc:1031-1058`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L1031-L1058): local send failure triggers application callback, whereas success updates shared `w4_evt`. Neither callback path preserves a UHID ID.
- [`bta/hh/bta_hh_main.cc:89,134`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_main.cc): write commands and handshakes are distinct messages dispatched in the BTA state machine.

## Safe implementation contract, not a patch

An identity-preserving transaction mechanism must distinguish:

| Stage | Example result | Provenance required | Kernel UHID action |
|---|---|---|---|
| API creation / enqueue | `bta_sys_sendmsg` | origin, kernel request ID, handle/session | **NO success reply** |
| No/invalid handle | `BTA_HH_ERR_HDL` | original request + local error | correlate failure; no fabricated success |
| Local transport rejects | no ACL, congestion, L2CAP write error | original request + local error | correlate failure; no fabricated success |
| Accepted local transport | `HID_SUCCESS` | keep ownership until real remote completion | **NO success reply** |
| Remote HID handshake | SET status | unique active command and generation, no stale callback | reply only if identity *proven* |
| Disconnect/timeout | pending owner uncertain | cancel/quarantine generation; stale replies ignored | no success reply; assess kernel timeout/error behavior |

**ABI concern:** appending fields to `tBTA_HH_CMD_DATA` in only one module is not safe; the struct is passed via `tBTA_HH_DATA` union, affected message allocation and dispatch must be built together. `rpt_id` is report number, not request ID. The default public BSP is not established as binary-compatible with Oranth.

**Engineering decision:** no kernel ACK writer until event identity and callback ownership are proven; no global L2CAP security relaxation. Native 0x22 authentication, Java bond policy and UHID SET reply remain independent gates. No M3 operations and no ARM32 build performed.
