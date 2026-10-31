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


## Follow-up: explicit kernel failure chain and stronger original-M3 evidence

This is a real **source-verified failure mechanism**, not merely a suspicious string.

**Upstream Linux v5.4** `drivers/hid/uhid.c`:
1. `uhid_hid_raw_request(HID_REQ_SET_REPORT)` calls `uhid_hid_set_report`, creates `UHID_SET_REPORT` with monotonically assigned request ID and waits for matching `UHID_SET_REPORT_REPLY`.
2. `__uhid_report_queue_and_wait` has a hard `5 * HZ` wait; missing reply, UHID teardown, or an uncompleted report results in `-EIO`.
3. `uhid_report_wake_up` ignores a reply with a different ID or wrong event type. A delayed/stale reply cannot be used to complete another request.
4. `uhid_hid_set_report` also returns `-EIO` when the reply indicates an error; a zero-error reply returns the report byte count.

**Upstream Linux v5.4** `drivers/hid/hid-sony.c`: the `SIXAXIS_CONTROLLER_BT` probe calls `sixaxis_set_operational_bt`, sending Feature SET_REPORT `F4 42 03 00 00`. On negative return it logs failed operational mode and branches to `err_stop`, before registering the Sony motion sensors / completing probe. Therefore **if the M3 stack is missing the proper matching UHID reply**, the kernel-side Bluetooth HID driver can fail to bind, even if controller authentication / L2CAP / Java policy were changed successfully.

**Important M3-specific positive evidence:** owner archived `dumpsys input` in the known **USB** test shows a separate **`Sony PLAYSTATION(R)3 Controller Motion Sensors`** device, plus main gamepad. Linux 5.4's `hid-sony.c` uses the distinctive suffix ` Motion Sensors` in `sony_register_sensors`, invoked in its DS3 USB path. The very close string/behavior match makes the Sony driver **strongly indicated as active on M3's USB path**, not merely theoretically available in Linux 5.4. However it is still not direct proof of `CONFIG_HID_SONY` or exact Bluetooth UHID Sony driver binding: an OEM downstream driver could exhibit the same behavior; the Bluetooth path must advertise correct bus/VID/PID and execute probe.

**Call ordering caveat:** UHID HID-driver probing and Bluetooth Java connected callback can be asynchronous; do not assert that Java admission always happens before or after the kernel's SET_REPORT timeout without M3-specific event evidence. They are separately required gates, not a guaranteed linear timeline.

References:
- Linux v5.4 UHID: https://raw.githubusercontent.com/torvalds/linux/v5.4/drivers/hid/uhid.c
- Linux v5.4 Sony: https://raw.githubusercontent.com/torvalds/linux/v5.4/drivers/hid/hid-sony.c
- Older Android Fluoride `bta_hh_co.cc` (request forwarded, reply stub): https://android.googlesource.com/platform/system/bt/+/54a50f50ca583146cd2556950177678d906e1391/btif/co/bta_hh_co.cc

## Offline function-address triage added

`experiments/m3-hid-apk/elf32_symbols.py` now parses **ELF32 ARM PT_LOAD + SYMTAB/DYNSYM** from private native artifacts with Python stdlib. `audit_uhid_support.py` includes any retained `bta_hh_co_set_rpt_rsp`, `uhid_read_event`, `btif_hh_setreport`, `bta_hh_co_send_hid_info` and `bta_hh_co_open` function symbol VMAs and mapping to **offline file offsets**. The output is only a pointer for later disassembly, **not** a live address or a verified hook. Stripped binaries can report no match despite code being present.

A local independently compiled **ELF32 ARM** synthetic test library validated the symbol and VMA→file-offset extractor; pure-Python synthetic fixture unit tests plus prior UHID marker tests: **11/11 PASS**. The private original M3 2024/2025 native `libbluetooth.so` bytes are not currently available in this execution context, so **no device-native function was claimed located or behavior verified**.

## Actual implementation contract if this bug is present

A legitimate M3 patch design must preserve **UHID request correlation** rather than blindly acknowledging any SET_REPORT: record the originating UHID request ID (bounded, associated with correct device/session), forward the original report to proper Bluetooth HID Host over its control channel, correlate the actual response/status to **the same ID**, deliver `UHID_SET_REPORT_REPLY` with correct status, and retire pending IDs on close/timeout. Correct negative statuses must be reported as failures, not fabricated success. Separate Bluetooth Native + Java admission and per-DS3 USB authorization still apply. No generic ACK, no global HID security weakening, no direct injection of F4 without source evidence, and no device modification approved.

## 2026-10-31 precision correction — ARM32 Thumb symbol mapping regression

A fresh actual **ARM32 Thumb** synthetic shared object compiled via `clang --target=armv7a-linux-androideabi21 -mthumb -nostdlib -fuse-ld=lld -shared` exposed an important bug in the new `elf32_symbols.py`: it previously treated odd ELF `STT_FUNC.st_value` as an actual instruction address for file-offset translation. The low bit denotes **Thumb instruction-set state**; it is **not part of the instruction address**. Original code mislocated each Thumb function by exactly one byte, invalidating subsequent disassembly from the reported file offset.

Concrete reproduction, based on the actual newly compiled test ELF:

| Value | Before | Corrected |
|---|---|---|
| Function | `bta_hh_co_set_rpt_rsp` | same |
| Raw ELF `st_value` | `0x121d` | retained as `symbol_value=0x121d` |
| Actual instruction VMA | incorrectly `0x121d` | `0x121c` |
| ELF file offset | incorrectly `0x21d` | `0x21c` |
| Architecture | ELF32 ARM, Thumb | explicitly `thumb=true` |

Fix in `elf32_symbols.py` computes `instruction_vma = st_value & ~1` for odd ARM function symbols and derives the load-segment file offset from `instruction_vma`, while retaining the raw `st_value` for provenance. `audit_uhid_support.py` now returns distinct `symbol_value`, `instruction_vma`, `thumb`, and `file_offset` fields. Both the ELF32 helper and top-level auditor have regression tests. **13/13 Python host-only tests PASS**; actual ARM32 Thumb test ELF also outputs the expected mapped offset. This only validates address bookkeeping on test ELF, **not actual M3 native UHID reply support**.

No actual M3 native ELF bytes were available in this session; no original firmware patches, live probes, or hook addresses are claimed. Any S8 original disassembly VMAs must continue to be tied to the exact SHA-pinned M3 binary and not reused for 2025 ELF or ASLR runtimes.

## AOSP version history caution

Old Android Fluoride `bta_hh_co_set_rpt_rsp` code has appeared in **more than one form**: one older implementation with UHID reply and ID queue was later removed in a downstream fork, other older AOSP snapshots log unsupported replies, while newer AOSP conditionally compiles reply handling behind `ENABLE_UHID_SET_REPORT`. Hence **neither Android 12 version label nor a present symbol/string proves M3 actually returns UHID_SET_REPORT_REPLY**. Require exact build callgraph or a separately approved narrowly scoped runtime observation, and never generate an ACK merely to make the kernel probe pass.

Source for old AOSP stub: https://android.googlesource.com/platform/system/bt/+/b512782fdf214367e0d1f8bb3751420e6cff1d39/btif/co/bta_hh_co.cc
Source for new conditional branch: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/0861bbd1b84dd8235878bad74fb60a4319ae9cbf/system/btif/co/bta_hh_co.cc
