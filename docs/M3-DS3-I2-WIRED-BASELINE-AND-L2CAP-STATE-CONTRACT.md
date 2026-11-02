# I2 — Wired baseline, one-time cable enrollment, and L2CAP state-machine contract

## Owner-verified requirements (not a hypothetical option)
- iMETBOX M3 + DS3 **already works over USB cable in RetroArch**. This is a demonstrated wired input baseline; do not rerun it without need.
- Owner explicitly accepts a **one-time USB setup / enrollment**. After that, expected everyday workflow is **USB disconnected, press PS button, Bluetooth wireless game input in RetroArch**.
- **One-time USB enrollment != proof of wireless Bluetooth bond/authentication.** DS3 feature report 0xF5 can program host/master BD_ADDR, but that does not mean Android has a conventional link key or BOND_BONDED. MAC matching alone is not cryptographic proof.
- A solution that demands leaving the USB cable connected for gameplay is **NOT ACCEPTED**; a solution that requires repeating the wired enrollment every session is also **NOT ACCEPTED**.
- Preserve USB working path and other Bluetooth devices. No global security relaxation, forged link key/bond, unapproved device modifications.

## Pinned source: exact inbound state transition
BPI-SINOVOIP/BPI-H618-Android12 @ `250eabfc529518b7f26432663ed0a867ab2f625d`, [l2c_csm.cc:267–311](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_csm.cc#L267-L311):
- Incoming BR/EDR `L2CEVT_L2CAP_CONNECT_REQ` captures remote BD_ADDR, PSM, and channel `p_ccb`.
- Sets `CST_TERM_W4_SEC_COMP` then calls `btm_sec_l2cap_access_req(... false, &l2c_link_sec_comp, p_ccb)`.
- If `BTM_CMD_STARTED`, responds `L2CAP_CONN_PENDING`. Any alternative must respect asynchronous security state/lifetime and response semantics.

[Inbound completion state handler l2c_csm.cc:445–528](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_csm.cc#L445-L528):
- `L2CEVT_SEC_COMP` transitions to `CST_W4_L2CA_CONNECT_RSP`. For Classic BR/EDR, when not awaiting information response it sets channel timer, sends connect response and config request; otherwise it sends pending.
- `L2CEVT_SEC_COMP_NEG` with `BTM_DELAY_CHECK` arms delayed-check timer; otherwise sends `L2CAP_CONN_SECURITY_BLOCK` for Classic and releases channel.
- Link disconnect calls `btm_sec_abort_access_req` and releases channel.
- Therefore **simply returning 'BTM_SUCCESS' from a local policy helper is NOT proven safe**. A future per-enrolled-DS3 authorization must integrate with these state and callback contracts without representing a nonbonded link as authenticated/encrypted.

## End-to-end acceptance gates
1. With USB, DS3 still detected and controllable in RetroArch (existing baseline).
2. Once-only authorized USB enrollment matches the current M3 Bluetooth adapter, controller identity and protected, revocable cable-paired record.
3. After USB unplug and PS-button action, the same enrolled controller connects on Bluetooth Classic HID PSM 0x11 and 0x13, without conventional PIN/link-key bonding if the chosen cable authorization contract allows it.
4. Java HID Host admits only the same cable-enrolled session without lying about `BOND_BONDED`, while retaining quiet-mode/deny policy for other devices.
5. UHID/Android InputManager exposes the wireless controller and Sony feature/report initialization completes correctly; RetroArch can navigate/play.
6. Controller remains usable wirelessly after disconnect/reconnect and normal device reboot without repeating USB enrollment (subject to explicit owner revocation or adapter change).
7. Unknown/spoofed devices and other Bluetooth profiles remain on original default security path; unexpected HID reports rejected, no keyboard injection.
8. Failing any gate means wireless acceptance **FAIL**, even if USB already works.

## Next offline checks
- Locate `l2c_link_sec_comp` implementation and its callback argument/state validation; do not inject synthetic success prematurely.
- Design host-only fail-closed session lifecycle tests (including simultaneous PSMs, disconnect, stale callbacks, revocation).
- Identify how source-integrated *explicit* cable authorization can be propagated to Java HID Host without changing ordinary bond state.
- Keep PR #51 separate. This document is **research only**; no M3 command, security downgrade, firmware patch, service restart or pairing attempt is authorized.
