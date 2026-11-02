# I2/I6 — Adopt previously researched BlueZ 5.83 cable-pairing design (no PIN reinvention)

## Decision: carry forward PR #50, not rediscover the DS3 authentication method

References already reviewed and established in [PR #50](https://github.com/franfran/android-bt-gamepad/pull/50):
- [BlueZ 5.83 decision](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-BLUEZ-583-DECISION.md)
- [Exact mechanism and Android implications](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-BLUEZ-583-MECHANISM-AND-M3-IMPLICATIONS.md)
- [Pairing implementation plan](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-PAIRING-IMPLEMENTATION-PLAN.md)

**Confirmed earlier conclusion:** Sixaxis/DS3 USB cable enrollment (feature 0xF5 writing Bluetooth host BD_ADDR) is *not* equivalent to conventional PIN/link-key bonding. BlueZ 5.83 implemented selective CablePairing handling; its behavior is the reference model, **not a library or API we can install into Android Fluoride unchanged**. In particular, the BlueZ implementation lowers initial PSM 0x11/0x13 listener security when cable-enrolled devices exist, then selectively enforces admission; **this is not a pre-auth, cryptographically proven, per-MAC-only exception**. Do not copy that adapter-wide intermediate exposure into M3 uncritically.

## New evidence integrated
Owner-uploaded HCI capture (analyzed and sanitized in [four-attempt report](M3-DS3-I2-UPLOADED-HCI-FOUR-ATTEMPTS.md)) shows four in-session sequences:
ACL connected -> HCI Authentication Requested 0x0411 -> Link Key Request -> host Negative Reply -> PIN Code Request -> no host HCI PIN reply -> about 30.06 seconds -> Authentication Complete 0x22 and disconnect. Independently, Oct 31 Java diagnostic records `pinRequestCallback` followed by `onPair: null`. **Do not cross-claim these separate dates as one session.**

Interpretation: the stock M3 path attempts conventional Bluetooth authentication of the DS3. This is consistent with the previously identified BlueZ cable-enrollment incompatibility. It does **not** establish a valid PIN value, nor prove that sending one fixes the connection.

## Contract for proposed *source-integrated* compatibility adapter

This is a **design contract, NOT GO for implementation or runtime deployment**.

### Trusted enrollment
1. Owner explicitly approves one bounded USB enrollment of one physical DS3. Verify real USB identity (VID:PID 054c:0268) and controlled session; store only minimal, protected local enrollment metadata; do not put controller MAC, host address, keys or raw captures in repo.
2. Verify the controller was actually programmed with this host's current Bluetooth address and that enrollment was not revoked. USB VID/PID, Bluetooth MAC, DS3 name or CoD alone do **not** cryptographically prove identity. A radio attacker may spoof address; high-risk HID inputs (keyboard-like reports) require restrictions even after an identity match.
3. Enrollment expires/revokes on host adapter change, explicit revocation, conflicting identity, or loss of provenance; reject ambiguous/stale sessions.
4. Never generate a fake link key, represent wireless PIN-less cable pairing as `BOND_BONDED`, or return fabricated authenticated/encrypted security flags.

### Native HID (Gate A)
5. A supported source integration must make the policy decision **before** HCI auth request, at a point where **both remote device/session provenance and HID PSM** (control 0x11 or interrupt 0x13) are available. If the callsite lacks this context, do not infer it from process-global state.
6. Default ordinary authenticated/encrypted handling for all other devices and services (especially keyboard devices) MUST remain unchanged. Pre-auth client-specific checks and rollback must be demonstrated; no blanket PSM-listener security downgrade.
7. Respect control-first channel ordering and maintain a bounded per-session state machine. Interrupt PSM cannot be admitted for a controller without corresponding authorized control channel/session. Reject mixed peers, reused handles, unexpected disconnects and stale callbacks.
8. If Fluoride cannot express this policy without unsafe security weakening, mark native adapter **NO_GO**. Source access alone does not guarantee safe integration.

### Java HID Host (Gate B)
9. OEM `HidHostService.okToConnect()` requires `BOND_BONDED` and acceptable policy. The source adapter **requires a separately reviewed, explicit trusted cable-enrolled state**, checked only in the narrowly authorized DS3 path, without altering generic Bluetooth bond state or quiet-mode/forbidden-policy behavior.
10. A valid Java decision must be bound to the *same native authorized session* and revoked with it; Java-only policy cannot fix earlier native authentication or HCI timeouts.

### UHID / input (Gate C)
11. The OEM SET_REPORT response gap is separate and was explored in PR #50 / source-first PR #51. A future adapter must preserve kernel UHID request ID, status, device and session correlation and retire on timeout/disconnect; do not send automatic success, reuse GET IDs, or rely on unsafe FIFO callback attribution.
12. Preserve normal devices, restrict untrusted keyboard/mouse-like input where feasible, and verify real RetroArch usability and controller feedback only after separate authorization.

## Architecture triage against PR #51

| Candidate | Verdict | Reason |
|---|---|---|
| PIN-only helper / guessed 6-byte host-address PIN | **NO_GO** | Prior BlueZ research rejects PIN assumption; uploaded HCI trace does not turn guessed bytes into protocol proof |
| Loadable driver or independent daemon | **NO_GO as presently scoped** | No supported Bluetooth profile plugin interface and no proven independent controller/PSM ownership |
| Global HID security downgrade | **NO_GO** | Exposes unrelated Bluetooth input devices before admission; no trusted per-device scope |
| Source-integrated M3 DS3 cable-pairing adapter | **RESEARCH GO only** | Coherent reference model but native pre-auth, Java policy, provenance and build/deployment requirements remain unresolved |
| PR #51 source-first UHID patch | **Keep independent** | Necessary later bridge investigation, not a solution to primary HCI PIN/timeout gate |

## Offline acceptance checklist (mandatory before any implementation GO)
- [ ] Locate exact pre-auth H618 source callsite with **remote address, PSM, connection/session identity** together. Verify conditions for both incoming PSMs.
- [ ] Demonstrate no adapter-wide security interval that permits unauthenticated keyboard/HID injection.
- [ ] Prove feasible trusted enrollment lifecycle, same-session native-to-Java authorization propagation and revocation (MAC-only is insufficient).
- [ ] Verify Java quiet-mode, forbidden policy and BOND_BONDED behavior for non-DS3 remain unchanged.
- [ ] Specify simultaneous requests, reconnect, stale callback, unrelated Bluetooth devices and malicious reporting tests.
- [ ] Confirm native ELF/Android build and recovery readiness before any deployment discussion. M3 injection remains NO_GO.
- [ ] Review PR #51's SET_REPORT request correlation and keep its changes isolated until Gate A/B are solved.

**No new pairing attempts, device actions, Bluetooth service restart, source/security patch deployment, raw log upload, firmware change or merging authorized by this document.**
