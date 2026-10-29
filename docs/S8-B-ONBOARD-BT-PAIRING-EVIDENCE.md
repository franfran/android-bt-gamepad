# S8-B — Onboard Bluetooth DS3 pairing evidence and decision tree

**Objective:** DualShock 3 wireless connection using the existing iMETBOX M3 internal Bluetooth controller, Android Fluoride/HID/InputManager, and the already working RetroArch DS3 mapping. No USB-baseline retest, external adapter, or permanent bridge is required by this track.

## Recovered historical M3 pairing evidence (2026-10-29 review)

Sources: [`docs/STATUS.md`](STATUS.md) and [`docs/ARCHITECTURE.md`](ARCHITECTURE.md), preserved from the earlier M3 investigation, plus [Issue #2](https://github.com/franfran/android-bt-gamepad/issues/2). This is a **review of recorded previous observations**, not a new packet capture or confirmation from currently loaded raw btsnoop data.

| Stage | Historical evidence | Assessment |
| --- | --- | --- |
| B0 Wired DS3 and enrolled host | Sony 054c:0268; USB `sixpair` set controller master to M3 adapter | **RECORDED PASS** |
| B1 BT attempt | DS3 PS-button flow initiated incoming HID Control PSM `0x11` attempt | **RECORDED ATTEMPT** |
| B2 ACL | Prior notes describe ACL/HID attempt and HCI auth sequence; no preserved authoritative connection-complete status/handle cited here | **CORROBORATED ATTEMPT, CONNECTION SUCCESS UNVERIFIED** |
| B3 Auth | Link Key Request → negative reply → PIN Code Request → host PIN response (6-byte adapter address) → `Authentication Complete 0x22` after ~30 s | **RECORDED FAILURE (LMP Response Timeout)** |
| B4 Bond | `BOND_BONDING` → `BOND_NONE`; no established LinkKey | **RECORDED FAILURE** |
| B5 HID | PSM `0x11` attempted; no successful HID control+interrupt channel establishment demonstrated | **UNVERIFIED / NOT CONNECTED IN EVIDENCE** |
| B6/B7 wireless input | No wireless Android InputDevice or working RetroArch demonstrated | **NOT PROVEN** |

**Implication:** The historical first *explicitly observed* failure is **HCI authentication status `0x22`**, not merely an Android Java HID bonded-device check. A host PIN command being accepted does not establish successful controller authentication. The exact reason for the controller-side LMP response timeout is still **UNKNOWN**; it may be a lower-layer interoperability issue and cannot responsibly be attributed to Java policy without additional evidence. The old raw HCI logs were intentionally excluded from the repository for privacy; do not invent missing HCI packet facts.

### Legacy source review already available

[`docs/ARCHITECTURE.md`](ARCHITECTURE.md) records legacy `libbluetooth.so` native HID registrations `hidh_conn_reg()` for PSMs `0x11` and `0x13` with security mask `0x36`, candidate `hidh_l2cif_connect_ind()`, `btm_sec_l2cap_access_req`, `btm_sec_auth_complete` and `btm_sec_pin_code_request`, and Android Java HID Host `okToConnect()` bonded-state gating. These are **historical static analysis references**, not validated live hook entry points; original ELF offsets are not current ASLR pointers.

### Decision / next research step

Do **not** repeat wired tests, generic PIN guesses, or static process maps. Re-examine the prior **authentication timeout flow** and distinguish **controller/host LMP exchange** from host-side **Fluoride security policy** and the later **Java HID bonded gate**. A scoped DS3-only cable-enrollment hypothesis is worth analyzing in an isolated source/test harness; no automatic live Bluetooth patch or injection is permitted. If raw historical traces are unavailable, the correct status is **cause unresolved at HCI 0x22**, not **pairing stage unknown**.

## Established vs unknown

**Established by owner:** wired DS3 works in RetroArch (before this repo was created); new USB `dumpsys input` corroborates Sony 054c:0268 Gamepad / Joystick and motion event delivery. S7 standalone ARM32 loader works in isolated targets; live Bluetooth process injection is not authorized.

**Still unverified despite recovered historical notes:** authoritative ACL connection-complete status/handle; exact root cause of the observed HCI 0x22 authentication timeout; successful HID channel establishment; current raw trace availability. Historical authentication failure and bond rollback *are* recorded in STATUS/ARCHITECTURE. **Do not infer an ACL link or failed authentication merely because ordinary pairing did not finish.**

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

1. Reuse recorded HCI 0x22 failure and bond rollback; locate original raw trace only if causal distinction is needed. Produce an evidence ledger with **source pointers** and B1–B5 statuses; do not turn an undocumented prior conversation summary into observed packet-level evidence.
2. If previous traces do not exist, design a **separately reviewed** bounded user-triggered connection observation plan using supported passive logs or normal UI; no auto-execution or live Bluetooth service modification.
3. In parallel, compare AOSP OEM-specific Bluetooth behavior, DS3 USB host-address conventions, and existing loader research at source level. State implementation hypotheses separately from observations.
4. Decide whether a pure application-level cable-assisted flow is feasible; if not, preserve native add-on architecture as a research candidate only. C4C-3 remains NO-GO.

## Acceptance criterion

Product milestone is *press DS3 PS button and play RetroArch wirelessly on M3's internal Bluetooth*. No claim of success until B2–B7 have device evidence. This document is a research plan, not authorization to test on live Bluetooth or to merge any Draft PR.
