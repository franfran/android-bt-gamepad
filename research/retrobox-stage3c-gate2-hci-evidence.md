# RetroBox — Stage 3C Gate 2: HCI authentication evidence & patch decision

**Status:** Confirmed HCI sequence; exact native patch site **not yet found**. No changes to M3. 2026-10-25.

## Inputs reviewed

- `/mnt/data/m3-ds3-btsnoop.log` (btsnoop v1, DLT 1002; 206 HCI records; parsed programmatically, not inferred from text screenshot).
- M3 Android 12 / API 31, Bluetooth HAL 1.0, `libbluetooth.so` ARM32, `Bluetooth.apk` with HID Host bonding logic (previous Gate 1 report).

## Verified chronology from HCI snoop

The following are 1-based btsnoop record indices, *not code addresses*.

| First attempt | HCI packet | Interpretation |
|---|---|---|
| #153 | HCI Event `0x17` | **Link Key Request** for DS3 `11:22:33:44:55:66` |
| #154 | HCI Command opcode `0x040C` | **Link Key Request Negative Reply** — host does not supply a stored link key |
| #156 | HCI Event `0x16` | **PIN Code Request** |
| #157 | HCI Command opcode `0x040D` | **PIN Code Request Reply**, six-byte PIN (previous HOST_MAC test) |
| #159 | HCI Event `0x06` | **Authentication Complete status 0x22**, LMP Response Timeout |
| #161 | HCI Event `0x05` | Disconnection Complete reason `0x22` |

Second attempt:

| Record | HCI packet | Interpretation |
|---|---|---|
| #196 | Event `0x17` | Link Key Request |
| #197 | Command `0x040C` | Link Key Request Negative Reply |
| #200 | Event `0x16` | PIN Code Request |
| #203 | Event `0x06` | Authentication Complete status `0x22` |
| #204 | Event `0x05` | Disconnection Complete reason `0x22` |

In second attempt no `0x040D` PIN Code Reply was recorded, consistent with the one-shot diagnostic app behavior. A successful HCI command completion on first attempt confirms command acceptance by the local controller, **not** authentication success or peer receipt.

## What this evidence changes

- Before a PIN prompt, Android/controller tries to find an existing **Link Key**; none is supplied. This is the standard legacy-key fallback flow; it does **not by itself prove** the root cause is an incorrect PIN, or that fabricating a link key would fix anything.
- Bond-state rejection in Java `HidHostService` is a **later** issue, distinct from the observed `0x22` authentication timeout.
- A kernel `L2CAP bind()` success cannot fix this: M3 has no `/sys/class/bluetooth/hci0`; Bluetooth HCI data traverses its vendor HAL and Android native stack.
- The current evidence **does not** show a successful cable-paired DS3 session, a successful link key notification (`0x18`), or completed HID L2CAP channels. No safe binary patch offset is validated.

## Gate 2 decision

**Do not edit `bt_config.conf`, inject made-up link keys, bypass global security, or patch a guessed Thumb instruction.**

Recommended next research implementation: compare the device-local incoming ACL / HID security policy against the Android 12 `system/bt/stack/btm/btm_sec.cc` and `stack/hid/` code and the explicit Sixaxis cable-pairing authorization in BlueZ; define a DS3-identity-scoped rule whose authorization is tied to USB pairing, not solely to public model name/MAC. Any rollout requires extracting exact Thumb control flow and a system-image-safe rollback mechanism before binary edits.

## Reproducibility

See `retrobox-stage3c-hci-audit.py`: parses this actual btsnoop, prints only security-related HCI events/opcodes and status/reason; does not include PIN or link key payloads.

## Public source reference

Android Bluetooth security manager reference (may differ from vendor build): https://android.googlesource.com/platform/packages/modules/Bluetooth/+/9194524a92/system/stack/btm/btm_sec.cc
