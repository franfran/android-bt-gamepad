# I2/I6 — Replace impossible cryptographic-oracle gate with explicit bounded-risk CablePairing policy

Status: source-informed architecture research; **NOT an owner approval to weaken security or deploy on M3**.

## New cross-check against original upstream BlueZ design

BlueZ issue #1165 (April 2025): https://github.com/bluez/bluez/issues/1165 explicitly proposes recording the DS3 MAC during USB pairing, admitting that known controller to HID without ordinary Classic bonding, and limiting HID events to the controller's capabilities. It explicitly acknowledges that an attacker can sniff and impersonate its MAC; this narrows exposure but does not establish cryptographic radio peer identity.

BlueZ v4 patch (Apr 24 2025): https://www.spinics.net/lists/linux-bluetooth/msg119483.html states `BT_IO_SEC_LOW` is required for cable-paired devices, and makes HID listener initially lower security when such a controller exists, with later per-device checks. This exposes a potentially **adapter-wide pre-admission interval**. Upstream BlueZ 5.83 release changelog (https://kernel.googlesource.com/pub/scm/bluetooth/bluez.git/+/refs/tags/5.83%5E%21/) records the Sixaxis cable-pairing fix.

These sources support **limited-risk nonbonded admission**, not a cryptographically authenticated live DS3. The exact M3 Android architecture, code ownership and security exposure are separate and unproven.

## Correction to the offline prototype's model

Current `experiments/m3-ds3-cable-session/ds3_session_model.py` uses `trusted_peer_proven`. This is only a symbolic oracle and **cannot be supplied from the DS3 MAC, VID:PID, Class of Device, or USB master BD_ADDR**. Requiring cryptographic proof as though ordinary DS3 supplied it would make the compatibility goal impossible by definition; silently setting the oracle `True` for an enrolled MAC would create false security assurances.

A future model should instead distinguish:
1. `usb_enrollment_verified`: physically attended one-time USB registration, exact adapter master address configured, stored with owner consent, revocation/version; DOES NOT authenticate the subsequent radio sender.
2. `radio_claim_matches_enrollment`: observed Bluetooth address matches an enrolled controller; spoofable by an active attacker.
3. `acl_hid_event_matches_epoch`: transient connection generation, channel PSM and callback are all correlated; prevents stale-event confusion but not radio impersonation.
4. `bounded_risk_policy_authorized`: consciously reviewed admission of a *nonbonded*, potentially spoofable controller under specific constraints, with owner approval before any runtime test.
5. `report_filter_proven`: actual HID device descriptor and report capabilities are validated and arbitrary keyboard/mouse injection paths blocked before untrusted reports reach UHID/InputManager.

**Current verdict:** (1) USB-first approach approved as a workflow but trusted storage/provenance implementation not built, (2) and (3) are known source-level design opportunities, (4) not approved for security modification, (5) not proven. Hence no implementation GO.

## Precise proposed acceptance gate

Allow candidate cable-enrolled HID admission *only if*:
- the enrollment record exists, is unrevoked and matches current adapter, and an actual physical USB enrollment step was positively observed;
- the radio source address matches it, with explicit acknowledgement this check is spoofable;
- transport BR/EDR; exact PSM 0x11 or 0x13; session/epoch valid; current channel association and per-session state valid;
- ordinary HID keyboard and non-DS3 traffic never enters exception path;
- input descriptor/report sandboxing prevents keyboard-like injection or otherwise aborts the program;
- there is a source-integrated protected Java permission path without forged bond state; security policy denies unrelated devices;
- all live deployment/security exception decisions have separate Owner review and adequate rollback.

No generic `BTM_SUCCESS_NO_SECURITY` return for global HID requests. No blanket security registration downgrade, no per-MAC-only `okToConnect`, no false `authenticated/encrypted` state. If pre-auth relaxation still exposes keyboard/unrelated HID before selective check, classify that design **NO_GO**.

## Next engineering proof, not another general architecture writeup

Map H618 `btm_sec_l2cap_access_req(bd_addr, psm, is_originator, ...)` into `btm_sec_l2cap_access_req_by_requirement(...)` and registered service security masks. Determine **exactly where before HCI auth** a narrow policy can substitute a *per-link/PSM decision* while retaining default registered security, and whether both PSM 0x11 and 0x13 safely reach it. Verify callback semantics; add host-only negative tests for unknown peer, unrelated HID and spoofed report descriptors. If no way to do this without a global exposure window, fail closed rather than assuming BlueZ's Linux listener approach safely ports to Android.

Owner acceptance invariant: wired USB already works in M3 RetroArch; USB cable once for enrollment is approved, afterwards wireless PS-button connection and repeated gameplay without recabling required.

PR #50 reverse-engineering archive and PR #51 full BSP source-first work remain independent; no M3 operations.
