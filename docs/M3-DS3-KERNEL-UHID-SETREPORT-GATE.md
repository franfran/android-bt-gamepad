# M3 DS3 Bluetooth input bridge — Kernel 5.4 HID Sony vs Android UHID SET_REPORT

**2026-10-31 — source audit and offline-only tools, no target operations.**

## New implementation-critical compatibility issue

The actual owner M3 hardware profile reports **Linux kernel 5.4.125+**, Android 12/ARM32. Linux upstream **v5.4** `drivers/hid/hid-sony.c` already includes both `HID_USB_DEVICE(SONY, PS3_CONTROLLER)` and `HID_BLUETOOTH_DEVICE(SONY, PS3_CONTROLLER)` in its device-id table (lines ~2754–2766). In the `SIXAXIS_CONTROLLER_BT` probe branch it invokes `sixaxis_set_operational_bt` with a Feature **SET_REPORT 0xF4**, bytes `F4 42 03 00 00`, and fails probe on a negative result. (This is distinct from its USB initialization.)

**Important limit:** upstream Linux v5.4 compatibility does not prove Oranth's 5.4.125+ kernel has `CONFIG_HID_SONY=y/m`, has not modified the Sony driver, or binds that driver to Bluetooth UHID. Archived M3 `dumpsys input` proves DS3 **USB** at `usb-sunxi-ohci-1/input0` with bus `0x0003` and `054c:0268`; it does NOT prove Bluetooth driver binding. No saved M3 `CONFIG_HID_SONY` or live Bluetooth `/sys/bus/hid/drivers/sony` snapshot has been verified.

Linux v5.4 Sony source:
https://raw.githubusercontent.com/torvalds/linux/v5.4/drivers/hid/hid-sony.c

## The decisive new bridge issue

Android Fluoride HID Host sends a Bluetooth HID device to the Linux HID subsystem by writing UHID descriptor with **`BUS_BLUETOOTH`**, vendor and product IDs; `/dev/uhid` is the adapter. The kernel's `hid-sony` Bluetooth probe may ask this adapter to transmit Feature SET_REPORT and wait for its response.

Source audit shows **version-dependent and incomplete** UHID SET_REPORT behavior:
- An older AOSP `btif/co/bta_hh_co.cc` `UHID_SET_REPORT` handler forwards the request to `btif_hh_setreport` when built under `OS_ANDROID`, but the separate `bta_hh_co_set_rpt_rsp` callback logs `UHID_SET_REPORT_REPLY not supported`. This means *request forwarding is not equivalent to proper request/reply completion*. Source: https://android.googlesource.com/platform/system/bt/+/b512782fdf214367e0d1f8bb3751420e6cff1d39/btif/co/bta_hh_co.cc
- A newer AOSP `bta_hh_co.cc` has explicit `UHID_SET_REPORT`, `UHID_SET_REPORT_REPLY` tracking under compile-time `ENABLE_UHID_SET_REPORT`; therefore modern documentation cannot prove the feature was compiled on a 2024 OEM Android 12 box. Source: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/0861bbd1b84dd8235878bad74fb60a4319ae9cbf/system/btif/co/bta_hh_co.cc
- Linux UHID documentation requires a matching `UHID_SET_REPORT_REPLY` ID after a SET_REPORT event. Source: https://docs.kernel.org/5.4/hid/uhid.html

**Consequence:** even if we eventually resolve pre-auth L2CAP and Java HID gate, the kernel may see an incomplete SET_REPORT transaction and fail DS3 Bluetooth initialization. Conversely if M3's exact stack supports SET_REPORT replies, this stage may work automatically. Both are presently **UNKNOWN**.

## Offline diagnostic delivered

`experiments/m3-hid-apk/audit_uhid_support.py` reads an owner-supplied **private offline ELF32 ARM** `libbluetooth.so` and optional archived kernel `.config`/config.gz. Reports SHA-256, ELF ABI, string-marker clues, and `CONFIG_HID`, `CONFIG_UHID`, `CONFIG_HID_SONY` values. The tool never opens the Bluetooth device, reads actual MACs or writes to the running service. Host-only fixture unit tests `test_audit_uhid_support.py`: **6 PASS** on a local equivalent implementation.

Example on an offline original ELF, if privately available:

```sh
python3 experiments/m3-hid-apk/audit_uhid_support.py \
  --elf /private/original/libbluetooth.so \
  --expected-sha256 4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85 \
  --kernel-config /private/kernel.config
```

The optional kernel-config argument can be omitted. Marker presence/absence **never proves real SET_REPORT functionality**: string may be dead/unreachable code, missing/stripped, or implemented with different wording. This is only a triage step before callsite-specific native disassembly. Do **not** claim green-light on a string match.

## Implementation/acceptance order

1. Owner's USB enrollment and wired RetroArch input already PASS; do not repeat.
2. Determine **actual M3 kernel** `CONFIG_HID_SONY` and Bluetooth UHID binding (archived files if available; future read-only observation requires approval if device interaction needed).
3. Analyze original SHA-pinned native `bta_hh_co_set_rpt_rsp` / `uhid_read_event` callgraph for complete SET_REPORT request **and reply**, not just strings or exported symbols. Original ELF is not currently accessible; cannot pronounce PASS/FAIL.
4. Then, only after earlier L2CAP/auth and Java Host gates are addressed, require wireless `InputDevice` plus actual Bluetooth-origin button report, not only enumeration.
5. Absolutely **do not** issue Feature F4 from a new plugin without first establishing whether kernel already sends it; duplicate injection can create races or unintended device behavior.

**M3 state remains NO_GO for live injection and system file patching.** Existing PR #50 is research-only, Draft; no device or firmware modifications.
