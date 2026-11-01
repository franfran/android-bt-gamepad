# S3 prerequisite: pinned H618 Fluoride SET_REPORT completion ownership

**2026-11-01 | Static source audit only | no M3 interaction or deployable patch.**

Base commit: `250eabfc529518b7f26432663ed0a867ab2f625d`, `system/bt` tree `d6f07310f73694977b301eac63d67b219ca20625`. All links are immutable:
- [UHID callout](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc)
- [BTIF report submission and callback](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc)
- [BTA handshake state](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc)
- [HID control PDU dispatch](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc)

## Positive, source-backed control-flow findings

1. `btif/co/bta_hh_co.cc:165-189`: `UHID_SET_REPORT` forwards report type, length and bytes via `btif_hh_setreport`; `ev.u.set_report.id` is **not forwarded or retained**. GET independently retains `ev.u.feature.id`.
2. `btif/src/btif_hh.cc:630-642`: `btif_hh_setreport` builds a `BT_HDR` with `create_pbuf`; allocation failure logs and returns **void**. It invokes `BTA_HhSetReport(p_dev->dev_handle, r_type, p_buf)`. No UHID ID/token crosses this API. Local failure cannot be conveyed back as a correlated SET reply through this function signature.
3. `stack/hid/hidh_conn.cc:678-682`: incoming `HID_TRANS_HANDSHAKE` calls `hh_cb.callback(dhandle, addr, HID_HDEV_EVT_HANDSHAKE, param, NULL)`. This carries handle and HID handshake parameter but no originating kernel request ID.
4. `bta/hh/bta_hh_act.cc:635-674`: `bta_hh_handsk_act` branches on `p_cb->w4_evt`. SET report case derives status from `bta_hh_get_trans_status`, calls `bta_hh_co_set_rpt_rsp(handle, status)`, then application callback, then clears `w4_evt = 0`. `w4_evt` identifies a **category**, not a transaction.
5. `btif/src/btif_hh.cc:893-901`: the BTA SET report event is delivered as a HAL `handshake_cb` using device address and status, also without UHID request ID. This is a *second* notification path, not proof of independent transaction completion.
6. `btif/co/bta_hh_co.cc:566-568`: the actual UHID SET completion callout only logs `UHID_SET_REPORT_REPLY not supported`.
7. `stack/hid/hidh_conn.cc:531-552,584-588`: disconnect/auth-failure paths can lead to `HID_HDEV_EVT_CLOSE`. This evidence does **not** establish correct retirement of a pending UHID SET ID or an explicit response to its blocked kernel waiter.

## Consequences and new audit questions

- The **identity is already discarded before BTIF → BTA**. A reply-only callout patch does not restore it.
- Even `one outstanding SET per device` is insufficient to prove attribution if duplicate or stale handshakes can arrive while a later request is active.
- `UHID_OUTPUT` with feature type also calls `btif_hh_setreport` (same file around line 127), but has no `UHID_SET_REPORT` transaction ID. It could collide with a kernel-initiated SET in native `w4_evt` handling. Do not assume every `SET_RPT_EVT` corresponds to a kernel SET.
- Separate Java/HAL originated `SetReport` calls use `BTA_HhSetReport` too (`btif/src/btif_hh.cc` around line 1576). Shared device state needs either serialization across **all** report producers or a reliable discriminator.
- Examine `bta_hh_act.cc` send command and BTA event queue scheduling to establish whether later commands can overwrite `w4_evt` before the first handshake. Source lines around 1030-1065 assign this field on certain commands.
- Determine native handshake timeout, retransmission, unsolicited handshake handling and disconnect/reset semantics before permitting reuse of any transaction identifier.
- Check `bta_hh_co_get_rpt_rsp` status handling for reference only. Never treat GET completion as proof that SET completion semantics are equivalent.
- Compare `UHID_SET_REPORT_REPLY` kernel ABI and status translation against actual M3 kernel header, not simply a newer Android Bluetooth module.

## Recommended source patch decomposition (not yet implemented)

**Phase 1 — observability/static proof:** map every `BTA_HhSetReport` caller, `HID_HDEV_EVT_HANDSHAKE` ingress, and `w4_evt` write/reset. Prove a single pending HID control transaction invariant or identify violations. Include allocation-failure and close with outstanding SET.

**Phase 2 — isolated, host-only C++ model:** represent origin as `KernelUhidSet{request_id, device_session}` versus `OutputFeature` versus `JavaHalSet`; explicitly forbid reply on non-kernel origin. Bound queue size and use fail-closed quarantine whenever attribution is indeterminate. Test interleavings, duplicate completion, producer collision and disconnect.

**Phase 3 — gated source patch:** introduce identity at UHID ingress; propagate a token through the state machine **only when its lifecycle can be established**; check exact original ID and safe status conversion before a kernel reply. No unconditional success ACK or global auth policy changes.

**Independent gates remain BLOCKED:** HCI authentication timeout 0x22; OEM Java `BOND_BONDED`/virtual-unplug policy. A native UHID patch alone cannot provide wireless DS3 operation.

**State:** source control flow directly verified; original M3 ELF alignment supported by PR #50 but no new binary inspection; no ARM32 build, no actual native callback-order proof, no device action, no runtime patch.
