# PR #52 — M3 Bluetooth Classic HID positive control: DualShock 4 wireless

**Date:** 2026-11-02 (Owner report). **Evidence class:** owner-reported live hardware acceptance, **not** an HCI trace or independently reproduced test. **Scope:** comparison baseline for DS3 **plugin feasibility** research only. **Status:** DS4 wireless gameplay **PASS (owner report)**; DS3 wireless **still FAIL/UNRESOLVED**. This document does not authorize a new architecture or a device change.

## Setup and directly reported result

- **Host:** iMETBOX M3 Android 12 TV box, using its existing onboard Bluetooth/OEM stack.
- **Controller:** Sony PlayStation 4 DualShock 4 (DS4).
- **Application:** RetroArch on the same M3.
- **Owner report (2026-11-02):** DS4 Bluetooth connection "**works out of the box!**" and, when asked specifically about RetroArch, "**all buttons works in RetroArch**".
- **Observed via owner report:** wireless DS4 pairing/connection was successful, RetroArch received gameplay button input, and the Owner reported all buttons functioning. This is a stronger positive control than a Bluetooth pairing notification alone.
- **No additional DS4-specific plugin/stack replacement/USB Bluetooth dongle was reported or required for this test.** The M3 is an already-rooted system; this observation does **not** establish a generic non-root environment or independently test every axis, rumble, reconnect-after-reboot, battery status or multi-controller interaction.
- No raw HCI snoop, adapter address, device identifier, pairing key, event timestamps or native Android input event trace was supplied. Do **not** fabricate these values.

## Bounded engineering interpretation

1. **Positive control:** the exact M3 device and existing OEM Android Bluetooth stack can support at least one Sony wireless controller through the **Bluetooth Classic HID -> Android input -> RetroArch** path, based on the Owner's live test. It demonstrates that an absolute claim that this M3 cannot support wireless PlayStation gamepad input would be false.
2. **Not a full DS3 diagnosis:** both DS3 and DS4 use Bluetooth Classic BR/EDR, but their enrollment, pairing, security and HID behaviors differ. DS4 working does not prove that DS3's precise failure cause has been located, nor does it prove DS3 can be fixed by a PIN helper.
3. **Maintain exact DS3 evidence:** the four previously captured DS3 HCI windows showed PIN Code Request, no **observed host PIN reply in those windows**, and Authentication Complete status `0x22` (**LMP Response Timeout**, **not** `0x05` Authentication Failure) approximately 30 seconds later. A separate earlier DS3 session reportedly contained a six-byte host PIN reply. These distinct sessions must not be conflated.
4. **Plugin feasibility unchanged:** DS4 success **does not create** any missing OEM removable plugin loader, native BTM/HID callback registration API, Java bond admission extension or UHID transaction hook. Existing PR #52 determination remains **NO_GO to implement** against presently verified public/installed supported extension interfaces; an exact 2024 OEM-private extension remains **UNRESOLVED** until exact original bytes / ABI are inspected.
5. **Testing value:** DS4 is now a known-good **wireless functional comparison** on this device, useful for later read-only A/B observations if explicitly planned. The DS3 repair objective remains independent.

## Acceptance snapshot

| Path | Evidence | Result | Limit |
| --- | --- | --- | --- |
| M3 OEM radio -> DS4 Bluetooth wireless | Owner direct report: "works out of the box!" | **PASS (owner reported)** | No protocol logs or latency measurement |
| M3 -> DS4 -> RetroArch buttons | Owner direct report: "all buttons works in RetroArch" | **PASS (owner reported)** | No separate independent per-button/axis audit |
| M3 -> DS3 USB -> RetroArch | Previously established Owner baseline | **PASS** | Wired only |
| M3 -> DS3 wireless -> RetroArch | Previous DS3 HCI investigations | **NOT WORKING** | No successful native auth/HID/input chain |
| Removable DS3 plugin using existing OEM radio | PR #52 bounded investigation | **Implementation NO_GO on verified interfaces; OEM-private ABI UNRESOLVED** | DS4 success does not change plugin authority |

## PR #52 boundary

Preserve this comparison as **documentation only**, without adjusting the plugin-only acceptance criteria. No Bluetooth service restart, root injection, OEM binary modification, alternative architecture, new USB dongle PR, live HCI probing, PR merge or deployment was carried out or authorized by this report.

For decision scope and HCI detail see [bounded plugin feasibility decision](M3-DS3-I1-PLUGIN-ONLY-FINAL-FEASIBILITY-DECISION.md) and [DS3 HCI 0x22 / cable enrollment evidence](M3-DS3-I2-HCI-0X22-BLUEZ-CABLE-PAIRING-VS-PLUGIN.md).
