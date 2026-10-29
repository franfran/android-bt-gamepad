# S8-B — Onboard Bluetooth DS3 pairing evidence and decision tree

**Objective:** DualShock 3 wireless connection using the existing iMETBOX M3 internal Bluetooth controller, Android Fluoride/HID/InputManager, and the already working RetroArch DS3 mapping. No USB-baseline retest, external adapter, or permanent bridge is required by this track.

## Established vs unknown

**Established by owner:** wired DS3 works in RetroArch (before this repo was created); new USB `dumpsys input` corroborates Sony 054c:0268 Gamepad / Joystick and motion event delivery. S7 standalone ARM32 loader works in isolated targets; live Bluetooth process injection is not authorized.

**Not established from the currently reviewed evidence:** exact last Bluetooth failure stage or error; existence of an ACL connection; authentication request/result; bonding state transition; HID control/interrupt channel establishment; whether any previous log captures sufficiently show each event. **Do not infer an ACL link or failed authentication merely because ordinary pairing did not finish.**

## Evidence-first protocol

Review **existing** historical observations and saved logs first. Record source file / commit / date and exact relevant event alongside the interpretation. Redact Bluetooth addresses, device serials, link keys, user identifiers and raw btsnoop payloads from issues. Keep raw originals locally.

| Gate | Evidence needed | PASS observation | If absent |
| --- | --- | --- | --- |
| B0 Controller identity | Original DS3 model and normal wired identity | Controller identified | Unknown |
| B1 Bluetooth visibility | M3 Bluetooth stack observes DS3 or directed connection attempt | Controller/device discovery or relevant connection event | Unknown |
| B2 ACL | HCI connection-complete / authoritative ACL connection | Status success with corroborating handle | Unknown |
| B3 Authentication | HCI/stack request and result with named status | Explicit success/failure result | Unknown |
| B4 Bonding | Android bond state transitions | Explicit BONDED / failed state with reason | Unknown |
| B5 HID channels | HID host control/interrupt connection events | Established relevant channels | Unknown |
| B6 Input | Android InputDevice created wirelessly, gamepad events | Actual DS3 input events | Unknown |
| B7 RetroArch | Mapped controller usable after USB unplug | Playable wireless gamepad | Unknown |

An unsuccessful user-level pairing attempt alone cannot label B2–B5 failed without corroborating logs. Controller-side host-address association and cable-assisted pairing are hypotheses to verify from existing evidence; never assume a generic Android pairing UI should work with DS3.

## Source/hypothesis separation

* **Known on M3:** USB DS3 is functional; Wi-Fi ADB available during normal operation; JNI library is SYSTEM and declared dependency names map in Bluetooth process. None of these proves Bluetooth authentication or HID transport.
* **Candidate design:** DS3-specific cable-assisted host association, constrained pairing handling in the existing Android Bluetooth stack, preserving other devices' security policies.
* **Unverified implementation:** where and whether OEM firmware exposes a DS3-special compatibility hook, whether an add-on could load from actual caller namespace, and whether reliable recovery is possible.
* **Prohibited shortcuts:** guessed PINs, fabricated link keys, global security downgrades, broad legacy-pairing exemptions, forcing a competing daemon to take the radio.

## Next actions without new M3 state changes

1. Locate prior pairing traces from project documents/issue history or locally retained logs. Produce an evidence ledger with **source pointers** and B1–B5 statuses; do not turn an undocumented prior conversation summary into observed packet-level evidence.
2. If previous traces do not exist, design a **separately reviewed** bounded user-triggered connection observation plan using supported passive logs or normal UI; no auto-execution or live Bluetooth service modification.
3. In parallel, compare AOSP OEM-specific Bluetooth behavior, DS3 USB host-address conventions, and existing loader research at source level. State implementation hypotheses separately from observations.
4. Decide whether a pure application-level cable-assisted flow is feasible; if not, preserve native add-on architecture as a research candidate only. C4C-3 remains NO-GO.

## Acceptance criterion

Product milestone is *press DS3 PS button and play RetroArch wirelessly on M3's internal Bluetooth*. No claim of success until B2–B7 have device evidence. This document is a research plan, not authorization to test on live Bluetooth or to merge any Draft PR.
