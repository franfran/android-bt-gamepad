# I2/I6 — Owner-uploaded M3 kernel configuration: Sony HID enabled

## Offline source and integrity
Owner re-uploaded `m3-kernel.config(1).gz`. Locally decompressed and parsed without contacting the device. Gzip size **31530 bytes**, SHA-256 **403e16be17169036dee77c1ba93b06f085b3f4a9376f7b51205a08e4a71410c7**; decompressed configuration **141529 bytes, 5295 lines**. Do **not** commit the binary unless owner separately authorizes; document only relevant configuration facts.

## Direct config results
```text
CONFIG_BT_BREDR=y
CONFIG_BT_HIDP=y
CONFIG_HID=y
CONFIG_HIDRAW=y
CONFIG_UHID=y
CONFIG_HID_GENERIC=y
CONFIG_HID_SONY=y
CONFIG_USB_HID=y
CONFIG_USB_HIDDEV=y
# CONFIG_HID_PLAYSTATION is not set
```

All lines above were read directly from the uploaded config, not inferred from public BSP. `CONFIG_HID_SONY=y` signifies built into the corresponding kernel configuration (not a loadable module). `CONFIG_HID_PLAYSTATION` being unset does not negate the older Sony DS3 `hid-sony` support.

## What this resolves and what it does not
**CLOSED:** earlier 'unverified M3 CONFIG_HID_SONY' evidence gap; `CONFIG_HID_SONY=y` and `CONFIG_UHID=y` are now directly shown in owner-supplied kernel config.

**OPEN:** establish provenance that the uploaded config exactly matches the currently booted M3 kernel; exact version/build and runtime driver bind; whether Bluetooth-over-UHID Sony 054c:0268 uses hid-sony rather than hid-generic; whether the kernel performs Bluetooth Feature SET_REPORT 0xF4 with `F4 42 03 00 00` after a successful Bluetooth HID attach; whether the existing stack completes the corresponding UHID SET_REPORT response, as studied in PR #51. A kernel config cannot itself prove these runtime outcomes.

## Engineering consequence
The kernel already appears appropriately configured for a Sony HID path; **do not propose installing hid-sony or rebuilding the kernel solely to enable CONFIG_HID_SONY**. Preserve PR #50 Linux `hid-sony.c` source findings (Bluetooth 0xF4 versus USB 0xF2). Prioritize the proven native Classic HID security and Java admission blockers; those prevent reaching UHID in historical attempts. On eventual separately authorized runtime validation, observe actual kernel Bluetooth driver binding, 0xF4 handshake and wireless input before claiming success. Do not inject 0xF4 twice.

**User workflow:** wired DS3 in RetroArch already proven; USB one-time enrollment authorized, wireless Bluetooth thereafter required.

**No M3 actions, new pairing, service restart, firmware/kernel modifications, security relaxation, or PR merge.**
