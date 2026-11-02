# I2/I6 — Archived evidence audit: kernel Sony HID and Bluetooth descriptor

**Scope:** read-only audit of existing PR #50 documentation, PR #52 artifacts, available conversation-upload evidence and prior HCI analysis. No new M3 command or pairing run.

## Evidence ledger

| Claim | Available evidence | Classification |
|---|---|---|
| DS3 works over physical USB in M3 RetroArch | Owner-confirmed working baseline; archived `dumpsys input` Sony joystick/motion sensor, USB `054c:0268` | **PROVEN wired only** |
| One USB setup acceptable; afterward BT wireless daily | Explicit Owner acceptance | **REQUIREMENT** |
| USB `0xF2` vs BT `0xF4` operational initialization | PR #50 `docs/M3-DS3-BLUETOOTH-OPERATIONAL-MODE.md` source analysis referencing Linux `hid-sony.c`; BT feature SET_REPORT `F4 42 03 00 00` | **SUPPORTED by upstream Sony source; M3 BT invocation not proven** |
| Bluetooth authentication fails before usable HID | Sanitized four-session btsnoop in PR #52: HCI AUTH_REQ -> LINK_KEY_REQ negative -> PIN_REQ with no host reply -> ~30sec timeout 0x22 | **PROVEN for captured attempts** |
| M3 kernel `CONFIG_HID_SONY` and real BT-to-`hid-sony` attachment | Previously supplied `m3-kernel.config.gz` is mentioned in prior project history, but no readable copy located during this current audit | **NOT VERIFIED HERE** |
| Original M3 over-Bluetooth SDP HID report descriptor/hash | Not found in reviewed PR #50/52 documents or current successful HCI attempt; authentication times out prior to HID data | **BLOCKED_EVIDENCE** |
| USB descriptor equals Bluetooth descriptor | No supporting capture | **NOT PROVEN; DO NOT ASSUME** |
| Kernel would send BT SET_REPORT 0xF4 automatically | Requires actual kernel config/driver binding and post-HID-init observation | **NOT PROVEN** |

## Why HCI logs cannot settle descriptor or Sony activation
The archived PIN/timeout attempts never progress to an admitted HID host session. These packets establish where native authentication fails, but cannot reveal Bluetooth SDP report descriptor acceptance, `UHID_CREATE`, Linux driver binding, feature `0xF4` submission, `UHID_SET_REPORT_REPLY`, or wireless input reachability. Likewise USB `dumpsys input` is not a Bluetooth fixture.

## Minimum next engineering steps using *existing* assets first
1. Recover exact historical `m3-kernel.config.gz` from Owner's retained artifact / private evidence repository when available; inspect `CONFIG_HID_SONY`, relevant `CONFIG_HID`, `CONFIG_UHID` and kernel version. **Do not infer flags from USB success or a generic H618 kernel.**
2. If `CONFIG_HID_SONY` is absent or unclear, inspect the archived OEM system/vendor kernel modules and original driver binding evidence, if already on disk; loaded module != built-in config setting. No new runtime commands implied.
3. Preserve distinct USB and Bluetooth descriptor fixture types. Use a private verified Bluetooth capture only when one exists; exact allowlist remains BLOCKED_EVIDENCE. Do not fabricate HID report lengths or IDs.
4. Before any future Owner-approved wireless trial, Native Gate A/Java Gate B must have a safe implementation and recovery plan. Then observe driver binding and 0xF4 automatically; **no extra 0xF4 injection without checking native/kernel behavior first**.
5. Preserve PR #51 SET_REPORT completion work as a separate prerequisite and audit its source-driven behavior before live use.
6. Final acceptance remains authentic DS3 wireless button/axis in RetroArch after one USB enrollment, including reconnect and reboot, with existing wired functionality intact.

## Practical design decision
The missing Bluetooth descriptor is a **downstream** gap. It is not presently rational to block source-level Native admission investigation solely on descriptor extraction when every captured wireless attempt dies in pre-HID authentication. Keep bounded-risk descriptor policy research parallel, but prioritize a proven narrow Native+Java cable-admission plan. Do **not** claim descriptor filtering alone solves MAC spoofing.

**Result:** offline audit complete; no newly recovered M3 kernel-config bytes or BT descriptor. PR #52 remains Draft/research only. No security change, install, restart, USB re-test, fresh pairing, firmware flash or merge.
