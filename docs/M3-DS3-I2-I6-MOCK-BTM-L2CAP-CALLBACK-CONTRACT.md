# I2/I6 — Offline mocked BTM → L2CAP callback model

Sources pinned to H618 `250eabfc529518b7f26432663ed0a867ab2f625d`:
- [`l2c_csm.cc:267–311`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_csm.cc#L267-L311): incoming BR/EDR CCB enters `CST_TERM_W4_SEC_COMP`, calls `btm_sec_l2cap_access_req(bda,psm,false,&l2c_link_sec_comp,p_ccb)`; `BTM_CMD_STARTED` triggers `L2CAP_CONN_PENDING`.
- [`l2c_link.cc:266–325`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_link.cc#L266-L325): native callback normalizes `BTM_SUCCESS_NO_SECURITY` to success, locates current LCB by address/transport, compares CCB pointer to callback ref, maps success to `L2CEVT_SEC_COMP`, `BTM_DELAY_CHECK` to timer, everything else to `L2CEVT_SEC_COMP_NEG`. Pointer check is not a session generation guarantee.

Two new Python-only research files:
- `experiments/m3-ds3-cable-session/mock_l2cap_btm.py` — mock ticket `{epoch,ccb}`, callback status transitions and stale handling.
- `experiments/m3-ds3-cable-session/test_mock_l2cap_btm.py` — ten tests spanning async PENDING→SUCCESS/FAILURE, synchronous callback, current success-no-security normalization, no callback ≠ success, delay, stale reconnect, duplicate, invalid CCB, invalid CMD_STARTED callback.

Run locally:
```bash
cd experiments/m3-ds3-cable-session
python3 -m unittest -v test_mock_l2cap_btm
```

**Critical caveat:** the mock does not run against native Fluoride, model a real thread scheduler, prove callback concurrency correctness or authorize unsecured HID. It intentionally treats an unmatched callback as STALE rather than asserting how stock source would handle it. Stock H618 comparison uses CCB pointer identity, not a minted epoch. A future implementation would need immutable callback token handoff and precise lifecycle ownership; no shortcut `BTM_SUCCESS_NO_SECURITY` on HID is authorized. The simulation cannot assert that a synchronous `BTM_SUCCESS` with no callback is a valid connection; it flags WAIT_CALLBACK for offline scrutiny.

**Test execution:** test source committed; execution status must be verified separately on a host. Do not claim real-world PASS or infer any M3 Bluetooth authorization success from mock events.

Next: verify current Java callback ordering and whether a session-bound grant can be consumed before kernel UHID creation; inspect gap between native BTIF device initialization and Java connected event. If UHID_CREATE happens before Java admission, descriptor-level policy must be native-first, not rely on Java rejection after the fact.

No live M3 commands, security changes, Bluetooth restart, merge or PR #51 edits.
