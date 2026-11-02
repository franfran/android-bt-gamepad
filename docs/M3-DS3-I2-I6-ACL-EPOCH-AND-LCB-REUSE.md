# I2/I6 — ACL connection epochs: HCI handle and LCB reuse

Pinned source: `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. Offline research only.

## Direct source findings
- [l2c_link.cc:138–207](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_link.cc#L138-L207): BR/EDR HCI connection-complete finds or allocates an LCB by peer address, sets its HCI handle with `l2cu_set_lcb_handle`, marks it `LST_CONNECTED`, and dispatches `L2CEVT_LP_CONNECT_CFM` to queued channels. A handle is an identifier **for this connection**, not an immortal identity/proof of peer authentication.
- [l2c_link.cc:337–374](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_link.cc#L337-L374): disconnect locates LCB by handle, marks `LST_DISCONNECTING`, dispatches disconnect to CCBs except `p_pending_ccb`, explicitly noting disconnect/reconnect race.
- [l2c_link.cc:380–439](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_link.cc#L380-L439): when channels/pending CCB remain, reconnect is started; BR/EDR can call `l2cu_create_conn_br_edr(p_lcb)` **without freeing the existing LCB**. Therefore pointer identity may be reused across distinct ACL connections.
- [btm_acl.cc:2593–2624](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/acl/btm_acl.cc#L2593-L2624): ACL connected calls `on_acl_br_edr_connected` upon HCI success; disconnect informs L2CAP/SCO/ISO and BTM security manager, with a host-reject-security reason special case.
- Existing PR #52 sources show BTA HID handle is retained through BTIF event transport but dropped at HAL/JNI address+state callback. BTA handle is **not** proven equivalent to ACL HCI handle.

## Concrete revision to proposed session registry
A durable USB cable-enrollment record is separate from an **ephemeral native connection epoch**.
- Mint a fresh non-repeating (for runtime lifetime) connection generation on each **new** BR/EDR ACL connection, even if LCB pointer, peer MAC, HCI numeric handle, or BTA HID handle repeats.
- Immediately invalidate previous grants on disconnect/start of reconnect, even if `p_pending_ccb` is preserved. Never infer continuation of authenticated/cable-authorized session from LCB reuse.
- Bind authorization to `{adapter_epoch, acl_generation, peer, transport, enrollment_generation, HID channel role, CCB lifetime}`; HCI handle / LCB / BTA handle are routing/context only, not sufficient trust.
- At event emission capture **immutable** generation and carry it across BTIF/JNI/Java queued callbacks. Java consumption must check exact epoch, current revocation state and policy, not query the latest connection by MAC.
- If source cannot propagate an immutable epoch without ABI break or trusted enrollment cannot justify a scoped exception, **fail closed / NO_GO**.
- Reload only enrollment (not prior ephemeral grants) after reboot and revoke on host adapter changes. Owner's workflow: proven wired USB RetroArch, one-time USB enrollment, thereafter Bluetooth wireless play and reconnect.

## Negative cases
1. Session A disconnects, LCB reused with same address and same HCI handle number for B: stale A grant must fail.
2. Pending CCB survives disconnect; B becomes connected; callbacks from A cannot advance B.
3. Delayed HCI/BTA/JNI event after teardown: reject as revoked.
4. Wrong transport, PSM, controller, enrollment generation or adapter epoch: default original security.
5. Legitimate bonded non-DS3 HID devices remain unchanged; no global downgrade and no fake `BOND_BONDED`.
6. A USB input device working in RetroArch does not imply Bluetooth ACL authentication occurred.

## Proof boundary
Source demonstrates LCB reuse and explicit disconnect/reconnect race handling. **It does not show a built-in ACL-generation field, nor demonstrate a safe plugin entry point or cryptographically authenticated DS3 peer**. Suggested generation registry is a source-integrated design requiring later code/test/ABI review; no implementation GO.

No M3 actions, no new pairing, Bluetooth restart, firmware edits, runtime injection, deployment or merge authorized.
