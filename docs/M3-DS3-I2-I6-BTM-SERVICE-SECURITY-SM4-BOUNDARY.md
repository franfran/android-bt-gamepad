# I2/I6 — Exact BTM service-security boundary and SM4 override

Pinned H618 source: `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. Source analysis only; no running Bluetooth changes.

## Source-grounded discovery

[stack/btm/btm_sec.cc:1701–1737](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L1701-L1737):

`btm_sec_l2cap_access_req(bd_addr, psm, is_originator, callback, ref_data)`:
1. Looks up the *registered* service record by **PSM + direction** through `btm_sec_find_first_serv`. Missing registration returns `BTM_MODE_UNSUPPORTED` through callback; an adapter must not convert unregistered PSMs to accepted services.
2. SDP has a special `BTM_SUCCESS_NO_SECURITY` callback and returns `BTM_SUCCESS`; **this is specific to SDP and cannot be generalized to HID**.
3. Computes `security_required` from the registered service security flags; Secure Connections mode transforms level-4 flags with `btm_sec_set_serv_level4_flags`.
4. Calls `btm_sec_l2cap_access_req_by_requirement(bd_addr, security_required, is_originator, callback, ref_data)`, **dropping PSM**. The earlier caller knows address, PSM, direction and CCB callback context; the requirement helper is no longer a safe generic PSM-specific decision point.

[stack/btm/btm_sec.cc:1488–1680](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L1488-L1680):
- Uses a per-peer `tBTM_SEC_DEV_REC` obtained by address, and the current BR/EDR HCI connection handle.
- If another security request or global pairing is in flight, requests may be queued/pending and callbacks retained.
- Under `BTM_SEC_MODE_SP` or `BTM_SEC_MODE_SC`, if `BTM_SEC_IS_SM4(p_dev_rec->sm4)` the helper **adds** `AUTHENTICATE | ENCRYPT` even after the service flags have been selected. Therefore simply setting service flags to zero at the caller is **not a demonstrated effective bypass**, and may have wider effects.
- Stores `security_required`, callback and `p_ref_data` into the per-peer security record and may invoke `btm_sec_execute_procedure`. Callback can be synchronous or deferred, and `BTM_DELAY_CHECK` is special.
- Conventional authenticated/encrypted security flags cannot be forged to admit a cable-paired DS3.

## Candidate seam and critical blockers

**Candidate to investigate, NOT approved code:** immediately after `btm_sec_find_first_serv` resolves a valid registered HID service and before the generic `by_requirement` helper, a source-integrated policy could *consider* an explicit cable-enrolled-session path while preserving ordinary security on every other request. The policy would need peer, PSM, direction, BR/EDR ACL epoch, enrollment generation, revocation and HID report constraints — none is supplied as a verified security capability by this function today.

**Do not implement naive variants:**
- `p_serv_rec->security_flags = 0` changes a shared registered service record and can affect unrelated HID; SM4 may force authentication/encryption anyway.
- `security_required = 0` is not enough to claim safe nonbonded service entry under SM4.
- `return BTM_SUCCESS` without precisely matching callback/CCB state machine may strand pending channels or grant an unauthenticated keyboard-like device.
- `BTM_SUCCESS_NO_SECURITY` for HID should not be inferred from its SDP special case.
- Widening `btm_sec_l2cap_access_req_by_requirement` universally is too late to infer PSM from arguments.
- MAC/name/CoD matching is spoofable. USB 0xF5 enrollment is controller configuration, not cryptographic radio identity.

## Next bounded proof
1. Inspect exact BTM service registration calls for HID PSM 0x11/0x13 and the shared security masks, verifying **which direction** of each service is registered and whether an earlier pre-auth path can trigger authentication independently.
2. Inspect the native L2CAP CCB callback contract under synchronous `BTM_SUCCESS` and deferred `BTM_CMD_STARTED`; the source has multiple return/callback shapes, so never assume an immediate bypass integrates cleanly.
3. Evaluate a *separate scoped authorization outcome* distinct from Bluetooth link authentication/encryption and capable of being passed to later BTA/BTIF and Java without forged bond state or broad HID exposure.
4. Trace HID descriptor/report filtering **before** accepting any potentially unbonded input; absent a credible filter plus explicit owner risk agreement, implementation remains NO_GO.
5. Pin evidence for actual M3 OEM native behavior separately from the public H618 reference tree.

## Decision
**Source seam: identified. Safe per-controller exception: NOT PROVEN.** Retain PR #50 archive and PR #51 source-first patch independently. Owner's verified wired RetroArch path and one-time USB setup → everyday wireless gameplay remain acceptance constraints. No device operations authorized.
