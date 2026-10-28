# RetroBox M3 — Stage 3C Gate 2: HID request precedes authentication

**Date:** 2026-10-25. **Source:** user-supplied `/mnt/data/m3-ds3-btsnoop.log`, parsed as btsnoop/H4 packets. No system changes made. **Finding:** The DS3's HID Control L2CAP request precedes the HCI authentication request. This narrows the native investigation to how the incoming HID Control channel triggers Bluetooth security.

## Why Link Key Request precedes PIN Code Request

In Bluetooth Classic legacy authentication, the controller asks the host whether a saved 16-byte Link Key exists, *even on a first connection*. If none exists, the host responds with **Link Key Request Negative Reply**. The controller then may request a PIN to create a new Link Key. A negative reply is expected, not an authentication failure in itself. The user-supplied DS3 capture shows this exact sequence. A successful PIN Code Request Reply command-completion means the local controller accepted the command; it does **not** prove that the remote device replied or that pairing succeeded.

Bluetooth SIG Core HCI specification: https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-61/out/en/host-controller-interface/host-controller-interface-functional-specification.html

## New finding: actual sequence at the HID security boundary

Relevant original btsnoop record numbers (1-based):

| Record | HCI packet | Interpretation |
|---|---|---|
| #144 | ACL, L2CAP signaling CID `0x0001`: `Connection Request` (code `0x02`), PSM **`0x0011`**, source CID `0x06F5` | DS3 initiates HID Control L2CAP channel |
| #147 | ACL, L2CAP signaling `Connection Response` (code `0x03`) | L2CAP connection response before authentication |
| #151 | HCI Command opcode `0x0411` **Authentication Requested**, handle `0x0080` | Host initiates link authentication *after* HID Control request |
| #153 | HCI Event `0x17` Link Key Request | Local controller asks host for existing key |
| #154 | HCI Command `0x040C` Link Key Request Negative Reply | No stored key supplied |
| #156 | HCI Event `0x16` PIN Code Request | Legacy pairing stage begins |
| #157 | HCI Command `0x040D` PIN Code Request Reply, length 6 | Diagnostic helper supplies 6 bytes; local controller accepts command |
| #159 | HCI Event `0x06` Authentication Complete, `0x22` | LMP Response Timeout |
| #161 | HCI Event `0x05` Disconnection Complete, `0x22` | Disconnect |

The HCI capture indicates **incoming HID Control channel followed by host-triggered authentication**, not an unconditional pairing prompt immediately on Bluetooth discovery. This is consistent with (but does not prove) Android's L2CAP/HID security requirements triggering the pairing attempt. A reverse-engineering target is therefore the security requirement for incoming HID PSM `0x11` and its Android stack callsite, not merely the generic PIN callback.

## What remains unknown

- Whether M3 would accept DS3 HID Control/Interrupt connections after a carefully scoped reduction in incoming HID security requirements.
- The precise stripped Thumb-2 function or branch responsible for triggering `HCI Authentication Requested` on this device.
- Whether downstream `HidHostService` bonded-state checks would reject a connection after L2CAP negotiation succeeds.
- Whether authenticating DS3 over legacy PIN is possible with a specific secret or requires bypassing ordinary bonding for cable-paired devices.

Do not modify `bt_config.conf`, synthesize Link Keys, globally disable Classic Bluetooth security, or patch guessed binary offsets. Restrict any future relaxation to USB-verified/cable-paired DS3 device identity; vendor/product or name alone is spoofable.

## Reproduce from HCI

Use `retrobox-stage3c-hci-l2cap-audit.py` on the original `m3-ds3-btsnoop.log` to list incoming L2CAP signaling and relevant security commands/events. The script deliberately omits raw PIN bytes and link-key material.
