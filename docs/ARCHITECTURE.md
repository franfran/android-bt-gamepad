# Why DS3 wireless needs Bluetooth-stack work

## User-visible goal

USB DS3 -> Android input subsystem -> RetroArch already works. Desired: DS3 Bluetooth HID -> Bluetooth HAL (UART) -> Fluoride legacy security manager -> HID host -> Android input -> RetroArch. Reusing RetroArch button mapping is downstream; it does not repair Bluetooth pairing.

## Observed pairing failure

`USB sixpair host configuration` → `DS3 wireless ACL/HID attempt` → `Link Key Request / negative reply` → `PIN Code Request` → `host PIN reply` → `Authentication Complete status 0x22 (LMP Response Timeout) ~30 sec` → `bond none`. The PIN command being accepted is **not** proof of authentication success.

The legacy controller expects a cable-pairing arrangement; Android 12's ordinary pairing/bonding pipeline is incompatible with this controller on the M3. Whether the exact root cause is firmware/LMP versus security-manager policy still needs instrumentation; do not state that a single Android bonded-device check is sufficient.

## Source-analysis findings

- `libbluetooth.so` legacy native HID code `hidh_conn_reg()` at ELF virtual `0x27E748`; incoming HID Control PSM `0x11` and Interrupt PSM `0x13` registered with security mask `0x36` (incoming/outgoing authenticate/encrypt). Addresses refer only to analyzed original build, **not** current ASLR absolute pointers.
- `hidh_l2cif_connect_ind()` at ELF `0x27EE28`; legacy `btm_sec_l2cap_access_req`, `btm_sec_auth_complete`, `btm_sec_pin_code_request` and related security functions mapped in `research/` stage3c notes. These are candidate instrumentation points, **not verified patches**.
- Android Java HID Host `okToConnect()` has bonded-state authorization logic on analyzed APK. Bypassing this broadly is insecure and cannot fix upstream HCI `0x22` alone.
- L2CAP kernel socket/bind success does not intercept UART-HAL owned controller traffic, explaining why a parallel kernel socket daemon was set aside.

## Implementation choices

Preferred experimental path: an inert add-on loaded into existing Bluetooth process, then passive tracing, followed only by narrowly scoped DS3 compatibility with **USB-proven enrollment**. Preserve other Bluetooth security. If runtime add-on cannot be made reliably recoverable, evaluate a version-matched controlled overlay/rebuild or fall back to USB — never speculative direct system library replacement.

References and prior disassembly observations: `research/retrobox-stage3b-compatibility-design.md`, `research/retrobox-stage3c-*`.
