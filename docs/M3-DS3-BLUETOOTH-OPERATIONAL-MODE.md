# M3 DS3 — Bluetooth HID operational-mode initialization (third acceptance stage)

**2026-10-31. Offline research and host-only tests, no device changes.**

## New upstream evidence: native DS3-specific activation

Linux `drivers/hid/hid-sony.c` contains `sixaxis_set_operational_bt()`, which submits **HID Feature SET_REPORT 0xF4**, byte sequence `F4 42 03 00 00`, in the Bluetooth-specific Sony gamepad path. The preceding code comment states that without the operational-mode initialization, the controller does not report input events. This is **not** the same as USB `sixaxis_set_operational_usb()`, which uses Feature GET_REPORT 0xF2 and is already known to work for the owner's wired M3 controller.

Authoritative reference:
- https://kernel.googlesource.com/pub/scm/linux/kernel/git/rric/linux/+/97d9d23dda6f37d90aefeec4ed619d52df525382/drivers/hid/hid-sony.c
- https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/7245b0017d1218042507e2f94129e1873ca29d6d/drivers/hid/hid-sony.c

AOSP Fluoride's HID Host callout `bta_hh_co_open` creates the HID input transport through `/dev/uhid`, which may then bind to a suitable Linux HID driver. The DS3 Bluetooth operational feature could therefore be handled by M3 **kernel hid-sony** automatically, if the driver/config/device IDs and callback path are present. We have NOT verified its USB/Bluetooth support in the exact M3 kernel; mere USB RetroArch PASS, M3 `dumpsys input` joystick/motion-sensor entries or presence of `/dev/uhid` are **insufficient proof** of automatic BT initialization. An alternative implementation might send the same report through another layer. **Do not automatically send this report twice, or assume a new native hook is needed.**

AOSP reference:
- https://android.googlesource.com/platform/packages/modules/Bluetooth/+/0861bbd1b84dd8235878bad74fb60a4319ae9cbf/system/btif/co/bta_hh_co.cc

## Resulting accepted evidence stages

1. **Native L2CAP/BTM allowed:** two HID PSMs may proceed without dropping unrelated devices' normal authentication. Existing M3 recorded HCI 0x22 remains unresolved.
2. **HID transport configured/connected:** Control 0x11 and Interrupt 0x13 negotiate successfully.
3. **Java Host admission:** exact M3 `okToConnect` currently requires `BOND_BONDED`, with virtual-unplug rejection.
4. **Linux/Android input device:** UHID device created and routed to expected driver.
5. **Actual DS3 wireless input:** a validated non-placeholder button/axis report arrives via the M3 built-in Bluetooth path and controls RetroArch. Stage 4 **alone does not prove stage 5**. For original DS3, Linux's Feature 0xF4 activation may be necessary unless already automatically performed.

## Existing physical M3 evidence

Archived owner `dumpsys input` from a *USB* session shows Sony DS3 joystick and separate Motion Sensors events and USB location `usb-sunxi-ohci-1/input0`, vendor/product `054c:0268`. This supports existing USB input capability, **not Bluetooth hid-sony binding**.

## Policy test correction

Commit `351b9ea` updates `experiments/m3-cable-policy/readiness_model.py` to require a simulated explicitly valid `wireless_report_observed(..., via_builtin_bt=True)` after `input_ready()`. Commit `d0157b4` adds tests that USB-only reports, invalid reports and early reports must not satisfy `operational()`. Direct local `unittest discover` against the updated sources: **20/20 PASS** (9 dual-channel, 11 readiness).

This simulator does not receive genuine runtime telemetry; its `valid` / `via_builtin_bt` booleans are test inputs **not security credentials**. A trustworthy on-device observer would need independent device attribution and session epoch correlation to exclude USB or stale callbacks before reporting success.

## Read-only next proof, when the Owner has a sanitized device snapshot

Check exact M3 kernel `CONFIG_HID_SONY` and whether Bluetooth UHID Sony `054c:0268` reaches `hid-sony`; do not confuse USB binding with BT binding. Prefer already archived kernel config and `/sys/bus/hid/drivers/` evidence before suggesting new device interaction. No user re-testing USB input; no actual Feature 0xF4 injection authorized.

## Safety

No new system permission, native injection, radio-security bypass, device restart, firmware flash, or claimed wireless success. PR #50 stays draft, C4C-3 remains NO_GO. The VCU risk remains *conditional*: actual M3 sending VCU and DS3 rewriting/clearing host address are not proven. See `docs/M3-DS3-HID-DEX-AND-NATIVE-GATES.md`.
