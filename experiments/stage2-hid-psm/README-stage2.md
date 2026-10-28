# RetroBox DS3 Bluetooth Stage 2 - HID PSM bind-only probe

This test has **not** been executed on M3. Stage 0 socket creation and Stage 1 temporary-PSM 0x1001 bind succeeded on the user's M3.

Stage 2 tests Linux AF_BLUETOOTH L2CAP `bind()` to the two well-known Classic HID PSMs used by DS3: **0x11 (Control)** and **0x13 (Interrupt)**. It binds each separately, does not listen or connect, and closes the socket immediately. No PIN, Bluetooth HCI, pairing, firmware, vendor stack, or configuration changes. Transient PSM reservation is possible during this tiny execution; avoid pairing attempts concurrently.

Run from the extracted directory:

```sh
DEVICE=192.0.2.10:1080
adb -s "$DEVICE" push l2cap_ds3_psm_probe_static /data/local/tmp/
adb -s "$DEVICE" shell su 0 chmod 755 /data/local/tmp/l2cap_ds3_psm_probe_static
adb -s "$DEVICE" shell su 0 /data/local/tmp/l2cap_ds3_psm_probe_static
```

Results: success proves the native Linux kernel L2CAP layer allows local binding the requested PSM at the instant of the test; it does **not** demonstrate DS3 authentication, a listening/accepting HID connection, or coexistence with Android's Bluetooth controller ownership and L2CAP implementation. If `errno=98` (EADDRINUSE), an existing kernel socket may own that PSM. Android userspace Fluoride may use its own L2CAP implementation, so even a successful Linux kernel bind does not mean incoming Bluetooth traffic will be routed into that Linux socket. If `errno=13`, check permission/capabilities. Source is provided for audit.

Static Linux ARM EABI binary built with Clang/LLD, without NDK or libc. File header inspected but not device-tested. SPDX-License-Identifier: MIT.
