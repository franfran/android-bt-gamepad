# I2/I6 — Bounded-risk offline policy model v2

Replaces the previous `trusted_peer_proven` symbolic cryptographic oracle with independently modeled gates:
1. Owner-attended USB enrollment + recorded abstract controller claim (not radio authentication)
2. Separate bounded-risk policy approval; **this is simulation only and grants NO real security exception**
3. Claimed BR/EDR peer matches enrollment record (**spoofable**), with event-bound ACL generation
4. Control PSM 0x11 then Interrupt PSM 0x13 in a simplified ordering assumption
5. Positive gamepad-only descriptor predicate before modeled Java admission / UHID_CREATE
6. Java quiet/forbidden checks, UHID completion, and per-report validation predicate before modeled UHID_INPUT
7. Revocation, adapter changes, re-enrollment, disconnect, and delayed callbacks invalidate old epochs

Run host-only tests:
```bash
cd experiments/m3-ds3-cable-session
python3 -m unittest -v
```
16 tests passed in isolated local execution. **No M3 communication or original Android stack code changes.** This is a toy state machine for policy consistency, not security evidence.

Caveats: `validated_gamepad_only` and `validated_report` are still stubbed booleans, **not parsers**; the model cannot stop a spoofed MAC, prove USB provenance for a radio peer, or establish a real pre-HCI-auth Fluoride exception. It also does not model concurrent devices, asynchronous callbacks, real HID connection negotiation, descriptor quirks, Bluetooth encryption, Java JNI ABI or Native/UHID ordering. An Owner approval to enroll once does **not** authorize changing real Bluetooth security. Before implementation, add grounded fixture parsers and trace/verify native callback timing; evaluate actual bounded-risk exposure explicitly.

Source reference: pinned H618 `hidh_conn.cc` registers HID PSMs with authenticate/encrypt; `btm_sec_l2cap_access_req` retains PSM before requirement helper; Java `okToConnect` demands bond, and `bta_hh_co` emits UHID_CREATE/INPUT. These paths are not modified by this model.

Readiness: offline prototype GO, real device implementation/deployment NO_GO; user USB wired gameplay already verified, wireless PS-button/reconnect remains acceptance target. PR #50/#51 separate.
