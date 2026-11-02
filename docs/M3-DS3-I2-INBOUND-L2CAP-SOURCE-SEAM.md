# I2 — Exact source-first inbound L2CAP cable-pairing seam

Pinned source: BPI-SINOVOIP/BPI-H618-Android12 @ `250eabfc529518b7f26432663ed0a867ab2f625d`.

## Source evidence
[system/bt/stack/l2cap/l2c_csm.cc lines 267–311](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_csm.cc#L267-L311):
- `L2CEVT_L2CAP_CONNECT_REQ` processes peer-initiated incoming L2CAP.
- On `BT_TRANSPORT_BR_EDR`, source holds `p_ccb->p_lcb->remote_bd_addr`, `p_ccb->p_rcb->psm`, and channel `p_ccb` in a single callsite.
- Calls `btm_sec_l2cap_access_req(remote_bd_addr, psm, false, &l2c_link_sec_comp, p_ccb)` while `p_ccb->chnl_state=CST_TERM_W4_SEC_COMP`.
- If security returns `BTM_CMD_STARTED`, sends `L2CAP_CONN_PENDING` to peer. This is the *pre-security decision boundary*, not proof that skipping security is safe.

[system/bt/stack/l2cap/l2c_csm.cc lines 222–239](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_csm.cc#L222-L239) has analogous outbound BR/EDR security call with `is_originator=true`. DS3 policy must first define whether the required runtime path is inbound or outbound; cannot assume both should be loosened.

[system/bt/stack/btm/btm_sec.cc lines 1701–1736](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L1701-L1736) resolves registered service security by PSM then delegates to `btm_sec_l2cap_access_req_by_requirement`, which has no PSM parameter. Therefore a future adapter must preserve PSM identity explicitly; cannot indiscriminately change service security requirements.

## Findings vs proof gaps
**PROVEN:** a source callsite contains remote address, PSM and live channel context before conventional security access request. More specific than prior ELF VMA alone.

**NOT PROVEN:** address/PSM/channel context constitutes cryptographic owner enrollment; any public API permits a third-party plugin; incoming HID control/interrupt authorization can safely coexist with normal authenticated/encrypted registered service mask; viable lifetime/epoch binding through callbacks and Java; exact OEM binary equivalence.

## Narrow source-integrated design contract for offline evaluation
- Device controller authorization must derive from owner-initiated physical USB enrollment and protected local state; MAC/name/CoD alone is spoofable.
- Reject unknown peers, non-HID PSMs, unrelated devices, changed host address, revoked state, stale or overlapping sessions, and interrupt-without-control. No global listener security downgrade.
- Preserve default `btm_sec_l2cap_access_req` for all requests unless *explicitly proven* eligible, with consistent callback/completion and timer behavior. Do not simply return `BTM_SUCCESS` and skip callbacks.
- Distinguish pre-auth exception from actual authenticated/encrypted state: never forge link keys, BOND_BONDED, security flags or synthetic success.
- Design explicit Java `HidHostService` cable-authorized admission and session revocation separately; a native-only patch remains incomplete.
- Keep PR #51 UHID SET_REPORT completion work separate and preserve request-ID/status correlation.

## Next research milestone
Read `l2c_link_sec_comp` callback and channel state transitions; inspect how BTM authorization can be scoped without weakening the PSM listener globally. Produce offline testable state model, incl. negative cases and a full *GO/NO_GO* decision before any source implementation.

**Research only:** no M3 operations, live pairing, reboot, Bluetooth restart, injection, build/deployment or security changes.
