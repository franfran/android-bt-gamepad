# RetroBox DS3 Stage 3C — Security policy model (host-only)

## What it does

This is a **source-level policy prototype**. It has no Android hooks, no injected code, no runtime patch, no access to Bluetooth resources, and cannot connect a DS3.

It models a narrow *candidate* selection for an **incoming** Bluetooth HID PSM (`0x11` or `0x13`) from a **USB-enrolled DS3** when the registered HID security mask is `0x36`. Everything else fails closed. Even for a candidate, the model does **not** change the security mask or authorize a connection; it only marks an event for possible future research.

The `confirmed_ds3_identity` and `usb_enrolled` flags are *test inputs*, not implemented security proofs. MAC address matching alone is not sufficient authentication.

## Run tests on macOS / Linux

```bash
cc -std=c11 -Wall -Wextra -Werror -pedantic ds3_policy.c test_policy.c -o test_policy
./test_policy
```

## Integration blockers

1. Confirm exact Android 12 legacy BTM access API and where both PSM and remote address are simultaneously available.
2. Verify M3 execution reaches that function for the DS3 connection; runtime GD flags are all `false`.
3. Implement durable, authenticated USB enrollment (not just MAC allowlisting) and explicit revoke.
4. Work out an upstream-style callback path through Bluetooth HID Host and its bond-state check.
5. Decide protocol/security consequences of unauthenticated or unencrypted BR/EDR L2CAP traffic before *any* relaxation.
6. Prototype with a buildable source variant and reversible install; avoid ad hoc patching `libbluetooth.so`.

**Do not flash or replace Bluetooth APK or .so based on this prototype.**
