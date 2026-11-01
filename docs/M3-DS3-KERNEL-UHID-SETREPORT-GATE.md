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

## Next decisive source-of-truth: ORIGINAL installed M3 ELF, not another test library

**Priority correction:** before comparing the 2025 International firmware's native implementation, inspect the **currently installed 2024 M3** `/system/lib/libbluetooth.so`. S8 established its expected SHA-256 as `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`. Neither original ELF nor the extracted 2025 ELF is actually mounted in the current research runtime (only original `Bluetooth.apk` is available). An ELF32 ARM synthetic test library validates tooling, **not M3 Bluetooth behavior**.

A source-verified older Fluoride branch includes `UHID_SET_REPORT` only within `#ifdef OS_ANDROID`, forwards its payload via `btif_hh_setreport`, but **does not record the kernel UHID request ID** and has a stub `bta_hh_co_set_rpt_rsp` logging that SET_REPORT_REPLY is unsupported. Meanwhile it **does** maintain a `get_rpt_id_queue` for GET_REPORT. That GET/SET asymmetry is a concrete signature of the historical incomplete implementation, NOT proof that M3 uses it. Evidence:
https://android.googlesource.com/platform/system/bt/+/b512782fdf214367e0d1f8bb3751420e6cff1d39/btif/co/bta_hh_co.cc

### Owner-run minimum **read-only** acquisition (only if prior original copy is absent)

```sh
# Mac/Linux; select the existing ADB serial, no system modification
adb devices
sh experiments/m3-hid-apk/collect_m3_native_readonly.sh \
  '<YOUR_EXISTING_ADB_SERIAL>' "$HOME/retrobox-private/m3-native"
# Expected installed 2024 SHA-256:
# 4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85
```

The script only performs an `adb pull /system/lib/libbluetooth.so`, plus an optional `adb exec-out cat /proc/config.gz`. It does NOT run `su`, pair DS3, restart Bluetooth, patch/flash the device, change SELinux or issue HID feature reports. It refuses repository-relative output and existing ELF overwrite. The operator may instead reuse/upload the original **private** `.so` previously supplied for S8; do not publish proprietary binaries in Git. A missing kernel config is nonfatal.

Once the actual 2024 ELF is accessible:

```sh
python3 experiments/m3-hid-apk/audit_uhid_support.py \
  --elf "$HOME/retrobox-private/m3-native/m3-original-2024-libbluetooth.so" \
  --expected-sha256 4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85
```

This first checks fingerprints, ABI, suspect logging strings and symbolic offline VMA/file-offsets. **Even a positive symbol/marker result is NOT a completed callgraph audit**. Next, original ARM32 disassembly must confirm the per-device `UHID_SET_REPORT` event dispatch, request ID preservation, actual response callback path and `UHID_SET_REPORT_REPLY` write. If it has only the old stub, label third gate FAIL and design a **real response-correlating bridge** offline; never forge ACKs to force driver probe. If full reply behavior is present, mark this bridge conditionally PASS and prioritize native authentication and Java HID admission instead.

The actual ADB step is **optional operator-initiated read-only evidence collection**; the existing S7-C4C-3 prohibition on live injection and device modifications remains unchanged.

## 2026-11-01: Actual original M3 native ELF and kernel config examined

The Owner uploaded the actual installed 2024 native ELF and a gzip-compressed kernel config. Both were inspected offline without any M3 device operation.

- Exact native ELF SHA-256: 4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85 (matches previously recorded S8).
- ELF32 little-endian ARM EABI5, Android 31, stripped. Build-ID: 0d29a62178e43066e018216c1f1d5b18.
- Actual kernel config: CONFIG_HID=y; CONFIG_HIDRAW=y; CONFIG_UHID=y; CONFIG_HID_SONY=y; CONFIG_INPUT_EVDEV=y. The kernel feature-build uncertainty is now RESOLVED; Bluetooth UHID binding remains unverified.
- Native ELF .rodata has the exact log string "UHID_SET_REPORT_REPLY not supported" at file offset 0x745bf (substring), with nearby "%s: Error: " prefix. It also contains "bta_hh_co_set_rpt_rsp" at file offset 0xb6899; "p_dev->get_rpt_id_queue" at 0x81e79; and "UHID_SET_REPORT: Report type = %d, report_size = %d" at 0x8c460.
- This cluster is strong original-M3 evidence consistent with the historically incomplete AOSP SET_REPORT response bridge. However, **strings alone do not prove the functions are reachable** or establish that no alternate working UHID reply path exists. The original ELF is stripped, so exact function callsites need actual Thumb/ARM disassembly and xrefs.

| Finding | Result |
|---|---|
| Installed original ELF identity | PASS |
| Kernel HID_SONY and UHID built in | PASS |
| Unsupported SET_REPORT_REPLY log marker in original ELF | PRESENT |
| Native callback execution and UHID reply callgraph | NOT VERIFIED |
| Real BT DS3 driver binding/input | NOT TESTED |
| Live injection/system patch | NO_GO |

Next offline step: map the native literal to compiled callback xrefs and search for any matching UHID_SET_REPORT_REPLY writer, explicitly accounting for ARM Thumb PC-relative loads. Never elevate a present marker to runtime proof. No proprietary binaries or kernel configs committed to Git.

## 2026-11-01 second pass: actual ARM32 ELF machine-code disassembly, evidence limit

A full native disassembly was produced from the **real owner-uploaded 2024 M3** `/system/lib/libbluetooth.so` using LLVM 17, alongside `readelf` inspection. This is no longer a synthetic ELF inspection. Exact binary SHA-256 matches S8 and Build-ID is `0d29a62178e43066e018216c1f1d5b18`.

- `.rodata`: file offset / ELF VMA `0x5fd30`, size `0xb9600`; `"UHID_SET_REPORT_REPLY not supported"` substring at `0x745bf`.
- `.text`: file offset `0x119e50`, ELF VMA `0x11ae50`, size `0x4c3fd8`. **Text offsets are 0x1000 behind corresponding section VMAs**, so using a raw file offset as disassembler start VMA without conversion would be an additional addressing error.
- The ELF is **stripped**: a direct `readelf -Ws` lookup of `bta_hh_co_set_rpt_rsp`, `uhid_read_event`, and `btif_hh_setreport` returns no function symbols. Their names appear in logging constants but **are not an ELF function-address map**.
- System `/usr/include/linux/uhid.h` enum confirms `UHID_SET_REPORT=13`, `UHID_SET_REPORT_REPLY=14`, and `UHID_GET_REPORT_REPLY=10`. Those constant values are independently supported by UHID ABI, but finding a constant 14 somewhere in a multi-megabyte binary would **not** prove an actual reply writer.
- An initial exact-pointer scan did **not** yield a clear, attributable code reference to the unsupported reply string. ARM Thumb PC-relative address construction and relocation/link-time folding must be accounted for. Do not misread unrelated matching words as valid xrefs or assume the absence of a literal pointer means dead code.

**Verdict: original kernel availability YES; M3 native binary has the unsupported-reply log constant YES; exact native SET_REPORT_REPLY writer/callback STILL UNKNOWN.** Evidence of a concrete code path writing a `struct uhid_event` with `type=14` through the actual device fd would make this a PASS, while proven active no-reply callback would establish FAIL. For now, no binary-patch offsets or conditional live experiments are justified.

### Reproducibility on private owner data

```sh
readelf -SW /private/m3-original-2024-libbluetooth.so | grep -E '\\.text|\\.rodata'
readelf -Ws /private/m3-original-2024-libbluetooth.so | grep -E 'bta_hh_co_set_rpt_rsp|uhid_read_event|btif_hh_setreport' || true
llvm-objdump -d --triple=thumbv7a \\
  /private/m3-original-2024-libbluetooth.so > /private/m3-original-thumb-disassembly.txt
```

Disassembly is **not** an injection, and this artifact must remain private: don't commit original ELF or full proprietary disassembly. A decompiler with ARM32 mixed-mode awareness, actual function recovery and data-flow tracking should next correlate `UHID_SET_REPORT_REPLY` (type 14), `write` to UHID fd, and the BTA response callback. Avoid treating symbol-less source matches as compiled M3 conclusions.

## 2026-11-01 third pass: exact compiled Thumb reference to unsupported reply log VERIFIED

Using the exact owner-original 2024 M3 native ELF (previously pinned SHA-256) and LLVM Thumb disassembly, a targeted scan for `ldr <reg>, [pc, ...]` followed by `add <reg>, pc` discovered an actual **PC-relative address construction** referencing the unsupported-reply error string and the callback's own name in the same code block.

| Thumb instruction VMA | Instruction | Evidence |
|---|---|---|
| `0x1a6ffa` | `ldr r1, [pc, #0x14]` | Literal pool at VMA `0x1a7010` |
| `0x1a7002` | `add r1, pc` | Literal signed displacement `-1256018`, resolves to `0x745b4` |
| `0x1a7000` | `ldr r2, [pc, #0x10]` | Literal pool at VMA `0x1a7014` |
| `0x1a7004` | `add r2, pc` | Literal signed displacement `-984943`, resolves to `0xb6899` |
| `0x1a7006` | `b.w 0x2c07c8` | Branch into logging-related native code |

The two resolved referenced C strings are EXACTLY:
- `0x745b4` = `%s: Error: UHID_SET_REPORT_REPLY not supported`
- `0xb6899` = `bta_hh_co_set_rpt_rsp`

**Higher-confidence finding than string scan:** This original firmware's executable code **does reference an unsupported SET_REPORT_REPLY logging branch in the named callback context**. File-offset mapping for the relevant Thumb instructions requires subtracting `0x1000` from these ELF VMAs because of its PT_LOAD layout (e.g. `0x1a6ffa` maps to file offset `0x1a5ffa`). The literal pool also lies in executable section, so do NOT try to interpret pool data at `0x1a7010` as instructions.

**Crucial remaining limits:** This code reference establishes a compiled log path, **not that every invocation of the callback reaches this branch**, and not absence of a separate native `UHID_SET_REPORT_REPLY` writer. Reachability/callers and all alternate reply writes still need dedicated control/data-flow recovery. Do not infer a working patch site from these address values, which are **offline VMAs, not actual process ASLR addresses or approved live hook points**. No device operation, library patch or injection performed.

## 2026-11-01 fourth pass: recovered complete original callback stub body

Recovered the original 2024 M3 ELF's **entire short ARM Thumb function** at ELF VMA `0x1a6fec` (file offset `0x1a5fec`), immediately before the literal pool and a different function at `0x1a701a`. Direct LLVM disassembly of exact original SHA-pinned bytes:

```asm
1a6fec: ldr     r0, [pc, #0x1c]    ; logging-flag pointer
1a6fee: add     r0, pc
1a6ff0: ldr     r0, [r0]
1a6ff2: ldrb    r0, [r0]
1a6ff4: cmp     r0, #0
1a6ff6: it      eq
1a6ff8: bxeq    lr                 ; disabled logging: immediate return
1a6ffa: ldr     r1, [pc, #0x14]   ; "%s: Error: UHID_SET_REPORT_REPLY not supported"
1a6ffc: mov.w   r0, #0x500
1a7000: ldr     r2, [pc, #0x10]   ; "bta_hh_co_set_rpt_rsp"
1a7002: add     r1, pc
1a7004: add     r2, pc
1a7006: b.w     0x2c07c8         ; tail branch to logging routine
1a700a: nop                       ; padding, followed by literal pool
```

Direct original ELF bytes starting at corresponding file offset `0x1a5fec`:
`07 48 78 44 00 68 00 78 00 28 08 bf 70 47 05 49 4f f4 a0 60 04 4a 79 44 7a 44 19 f1 df bb 00 bf`.

The PC-relative pool resolves to two C strings at ELF VMAs `0x745b4` and `0xb6899`. Both fall inside proprietary ELF `.rodata`, and the strings exactly identify the unsupported operation and callback name.

**Defensible improved conclusion:** The identified `bta_hh_co_set_rpt_rsp` compiled native function is a **logging-only/no-op callback**. When logging disabled, it immediately returns. When logging enabled, it tail-calls logger and does not construct a UHID event or write a reply. This is now executable-body proof, not just a string xref. A normal invocation of this callback therefore cannot complete the kernel UHID SET_REPORT_REPLY transaction. **Caveat:** the rest of stripped M3 code has not yet been exhaustively examined to rule out another callback/writer; nor has live reachability from a DS3 event been observed. Therefore label the *specific callback* FAIL and *end-to-end device behavior* still CONDITIONAL/UNVERIFIED.

This is a source-level **design blocker candidate**, not evidence that it caused the historical DS3 HCI auth error `0x22`: the auth failure occurs earlier than kernel HID probe. An eventual compat fix must preserve per-request UHID ID/status correlation and cannot simply force a generic OK or change security for unrelated devices. M3 live injector remains NO_GO; no owner device actions.

## 2026-11-01 fifth pass: real callsite into compiled no-op callback

The owner-original ELF disassembly has yielded a **direct Thumb BL callsite** to the previously recovered `bta_hh_co_set_rpt_rsp` logging-only stub:

```asm
0x15ca08: push  {r4,r5,r6,r7,lr}
...
0x15ca54: ldrh  r0,[r4,#0x1c]
...
0x15ca88: cmp   r0,#5
0x15ca8e: bne   0x15cb1a
0x15ca90: uxtb  r1,r1
0x15ca92: mov   r0,r2
0x15ca94: bl    0x1a6fec     ; documented logging-only callback
0x15ca98: b     0x15cb18
```

This adds **compiled caller evidence**. It shows a callback dispatch path branches on a 16-bit field at offset 0x1c equal to **5**, then directly calls the no-op `0x1a6fec` function. **Do NOT misidentify 5 as Linux UHID event type 14**: the field belongs to the native callback dispatch context and its precise enum needs separate evidence. The same handler has a branch for field value 4 that calls `0x1a7018`, a different native helper.

This observation significantly corroborates that the logging-only stub is not just orphaned debug text. Its *runtime activation in an actual DS3 session* remains unobserved. Other `UHID_SET_REPORT_REPLY` writers elsewhere in the ELF have not yet been exhaustively excluded. The documented kernel requirement is a matching UHID event with `type=14`; the stub `0x1a6fec` can never fulfill that requirement.

For the 2024 M3 native binary, **callback-level finding: FAIL (no-op)**, **complete per-device UHID handshake: UNVERIFIED**, **live DS3 wireless: NOT TESTED**. HCI auth error 0x22 occurs prior to this HID probe path. Do not ship a patch based solely on this callsite; actual request-id correlation and Java admission still unresolved.

## 2026-11-01 sixth pass: establish callback event enum 5 as BTA_HH_SET_RPT_EVT

Historical Fluoride callback enum definitions are version-dependent:
- Legacy `platform/system/bt` source `bta/include/bta_hh_api.h` defines `BTA_HH_GET_RPT_EVT=4`, `BTA_HH_SET_RPT_EVT=5`. Verified against https://android.googlesource.com/platform/system/bt/+/master-soong/bta/include/bta_hh_api.h
- A later `platform/packages/modules/Bluetooth` version inserts `BTA_HH_EMPTY_EVT=0` and shifts the same events to `5` and `6`. See https://android.googlesource.com/platform/packages/modules/Bluetooth/+/55843315dc7788857388a00c2e9026f626f21701/system/bta/include/bta_hh_api.h . **Do not apply newer enum offsets to the M3 binary.**
- Legacy `bta/hh/bta_hh_act.cc` handles SET handshake acknowledgements and explicitly calls `bta_hh_co_set_rpt_rsp(handle,status)` when `w4_evt == BTA_HH_SET_RPT_EVT`. Source https://android.googlesource.com/platform/system/bt/+/c110eca93d69fc336a81360fc22a1e439297f634/bta/hh/bta_hh_act.cc

Actual M3 owner-original 2024 ELF dispatcher `0x15ca54` loads halfword event from `[r4+0x1c]`; `0x15ca88` compares `r0` to 5; `0x15ca94` branches to the complete logging-only stub at `0x1a6fec`. The neighboring event 4 branch goes to separate `0x1a7018` helper, matching the distinct GET report callback in older Fluoride. This is strong combined **actual-M3 instruction evidence plus matching contemporary source-semantic evidence** for identifying event 5 as SET_REPORT completion; not merely an arbitrary callback index.

**Updated finding:** on the identified M3 native SET_REPORT completion path, the intended `bta_hh_co_set_rpt_rsp` callback does NOT issue kernel `UHID_SET_REPORT_REPLY`. Thus the original callback is a confirmed implementation gap and the Bluetooth DS3 `hid-sony` probe is at risk if it depends on this mechanism. However, this is **not proof** that a particular DS3 session reached the callback, and an unrelated alternate kernel reply writer is still not exhaustively excluded. It also cannot explain the previously measured *earlier* HCI authentication timeout 0x22.

Before any design or patch, do an original-binary read-only search for *other* UHID type 14 writers and whether the GET-report request ID queue is reused for SET. A correct future fix needs a per-device bounded SET-request ID queue, true result/status mapping, matching-ID UHID reply, timeout/disconnect cleanup, and no fabricated OK. No live M3 patch/injection authorized.

## 2026-11-01 seventh pass: original M3 GET-vs-SET asymmetric dispatcher

Reverified the uploaded 2024 native ELF SHA256 and directly disassembled its real callback dispatcher. Native event handler at `0x15ca08` reads the event halfword `[r4,#0x1c]`, uses a Thumb `tbb` dispatch, and has two separate report branches:

- **SET_REPORT event 5:** `0x15ca88 cmp r0,#5` then `0x15ca94 bl 0x1a6fec`, pointing to the SHA-verified **log-only SET_REPORT response callback**. It subsequently continues towards native upper-layer callback/event cleanup, **not UHID_SET_REPORT_REPLY**.
- **GET_REPORT event 4:** `0x15cb04 cmp r0,#4` then `0x15cb14 bl 0x1a7018`, an entirely different helper. Its full internal semantics must be audited separately; merely reaching it doesn't prove its queue/reply success.
- Nearby upper-layer indirect callbacks at `0x15cb28` and housekeeping at `0x15cb2c` are **not proof** of a successful kernel UHID write. A callback dispatch and UHID transaction completion are different responsibilities.

A new **fail-closed exact-original-byte verifier** `experiments/m3-hid-apk/verify_m3_report_dispatch.py` now pins the full 2024 ELF SHA and exact instruction bytes at these six positions: `0x15ca88`, `0x15ca94`, `0x15cb04`, `0x15cb14`, `0x1a6ff6` and `0x1a7006`. All six instruction slices have been independently checked byte-for-byte against the user's original uploaded ELF. The verifier returns explicit `reply_writer_exhaustively_excluded=False` and `runtime_reachability_verified=False` because those are NOT proven.

**Updated engineering verdict:** The **documented original SET completion callback** is confirmed broken/no-op for UHID reply; asymmetry versus GET is demonstrable in compiled M3 code. Another writer elsewhere is still not ruled out, and neither this gap nor a hypothetical remedy addresses the earlier 0x22 HCI authentication failure. This analysis is offline only; no user M3 modifications, no pair attempt, and no live patch authorization.

## 2026-11-01 eighth pass: actual M3 GET_REPORT reply construction and queue ID path

Read-only disassembly of the owner-uploaded original 2024 SHA-pinned ELF recovers the `GET_REPORT` helper starting at `0x1a7018` and confirms the actual native reply path, with more detail than prior event-dispatch evidence:

| Native Thumb VMA | Instruction/meaning |
|---|---|
| `0x1a7066` | Lookup per-device state |
| `0x1a7070` | Load pointer at per-device +0x28, branch if empty |
| `0x1a707a–0x1a7084` | Read and decrement byte queue-count field at +0x2c |
| `0x1a7088` | Call queue helper `0x2b430c` (element retrieval, semantic details still require verification) |
| `0x1a709a` | `movs r0,#0xa` = **UHID_GET_REPORT_REPLY type 10** |
| `0x1a709c` | `str r0,[sp,#8]` sets outgoing event type |
| `0x1a709e–0x1a70a0` | Loads a queue element's 32-bit request ID and stores it into event buffer |
| `0x1a70a8` | Stores report status/size field (exact structure field interpretation needs care) |
| `0x1a710c–0x1a7110` | Loads fd from per-device field +0x10, sets event pointer, calls `0x1a5fb0` |
| `0x1a5fb0–0x1a5fc0` | Repeated syscall wrapper call via imported function at `0x5dfe70`, with event write size `0x111c` |

In `0x1a5fb0` code, register args are r0=fd, r1=buffer, r2=`0x111c` before `blx 0x5dfe70`, consistent with `write(fd,event,sizeof(event))`. The helper handles interrupted/short writes; exact imported symbol can be correlated with relocation for definitive libc name. It is therefore no longer just a hypothetical native GET_REPORT helper: original code **constructs UHID type 10 with a stored ID and passes it through a real write-like helper**.

By contrast, original event 5 dispatch `0x15ca94` invokes the `0x1a6fec` *logging-only* `bta_hh_co_set_rpt_rsp` callback. This code is missing the analogous SET_REPORT reply event construction. **Callback-level SET reply gap is CONFIRMED.** It remains a separate task to exclude other `type=14` writers and verify the exact native kernel probe path in a real DS3 session. Do not say that this causes HCI auth failure 0x22 (it occurs earlier).

Potential minimal remediation must use a bounded per-device pending-SET-report queue, preserve exact UHID request ID from `UHID_SET_REPORT`, correlate actual Bluetooth status, send `UHID_SET_REPORT_REPLY (type 14)` via original UHID fd with correct error and cleanup on disconnect/timeout. The original GET queue is a useful reference but must **not be shared** indiscriminately: GET and SET requests may be concurrent, IDs must be correlated by event kind and device. Never manufacture success status. No new system/APK patch or live hook was performed.

## 2026-11-01 ninth pass: verify original GET reply guard, queue, and write-like contract

Re-read original owner-provided SHA-pinned M3 ELF using `llvm-objdump --triple=thumbv7a` (without relying on incorrectly labelled stripped symbols). Confirmed exact instruction-level dataflow:

- `0x1a7066`: helper lookup from HID handle; `cbz r0` at `0x1a706c` skips the normal reply path if no device.
- `0x1a7070–0x1a7080`: checks per-device pointer at `+0x28`, fd at `+0x10` (`bmi` if invalid), and pending queue count byte at `+0x2c`; skips reply on a zero count.
- `0x1a7082–0x1a7088`: decrements queue count and calls `0x2b430c`; `0x1a709e–0x1a70a0`: reads a 32-bit value from the returned queue object and stores it as UHID request ID.
- `0x1a709a–0x1a709c`: writes `UHID_GET_REPORT_REPLY=10` to the outgoing `uhid_event` buffer.
- `0x1a70a4–0x1a70a8`: writes the callback's returned status and report length to event fields. Full exact status conversion should be checked separately; no presumption that a success status is always justified.
- `0x1a70fa–0x1a7110`: copies report payload for suitable length, loads the checked per-device fd and calls the common output helper `0x1a5fb0`.
- `0x1a5fb8–0x1a5fc0`: helper sets `r0=fd`, `r1=event_buffer`, `r2=0x111c` and invokes an imported write-like function through `0x5dfe70`. On `-1`, checks errno and retries `EINTR=4`. To be precise, the imported PLT name has not yet been resolved in this pass; the calling convention and errno behavior are **consistent with write()**, not formal proof of relocation target.

**Comparison with SET:** report event 5 from native dispatcher at `0x15ca94` leads to the fully recovered no-op `0x1a6fec` callback, not to this queue-consuming type-10 writer. GET's per-device queue should **not** be reused unchanged for SET: concurrent GET and SET requests need type isolation, matching originating UHID ID, bounded per-device storage, correct completion-status mapping, and teardown cleanup. There is still no proven active alternate UHID event-type 14 writer, and no evidence that the HCI auth timeout 0x22 was caused by this later bridge.

This was a read-only re-examination of the private original M3 ELF; no M3 device communication, ELF patching, or hook was performed.

### Imported writer identification resolved in the same original ELF

Additional static relocation proof resolves the generic write-like call to actual libc `write`:

- ELF `.plt` at VMA `0x5dee30`; the referenced PLT entry `0x5dfe70` is 0x1040 bytes into `.plt`, or slot 260 of the 16-byte-entry region.
- ELF `.got.plt` at VMA `0x5ff534`. Relocation `R_ARM_JUMP_SLOT` at **`0x5ff948`** resolves to **`write@LIBC`** (visible in `readelf -rW`).
- The PLT/GOT slot correspondence supports `0x5dfe70` as the `write` trampoline. At `0x1a5fbc` caller explicitly sets `r2=0x111c` then `blx 0x5dfe70`. Error path at `0x1a5fca–0x1a5fd2` checks `errno==EINTR(4)` and retries, characteristic of the same `write` wrapper.

**Original M3 GET_REPORT_REPLY writer now verified as libc write via actual relocation**, rather than only a suspected write-like call. This does not prove SET_REPORT_REPLY event 14 writer exists.

## 2026-11-01 tenth pass: actual UHID_SET_REPORT ingress is distinct from GET request-ID enqueue

**Direct new original-M3 evidence.** The same owner's SHA-pinned 2024 native ELF was disassembled with `llvm-objdump -d --triple=thumbv7a`; verified the PC-relative xref `0x1a6980 ldr r1,[pc,#0x1cc]` / `0x1a6982 add r1,pc` resolves to the literal `UHID_SET_REPORT: Report type = %d, report_size = %d` at **`0x8c460`**. This identifies a compiled **UHID_SET_REPORT ingress branch**, not just a comment or leftover literal.

The neighboring **GET_REPORT** code demonstrates actual queueing:
- `0x1a692a ldr.w r1,[r10,#0x28]`: existing per-device pending GET-ID queue pointer.
- `0x1a692e ldrb.w r0,[r10,#0x2c]` → `0x1a6932 add.w r0,r0,#1` → `0x1a6936 strb.w r0,[r10,#0x2c]`: increment GET queue count.
- `0x1a693c movs r0,#4` → `0x1a693e bl 0x2b280c`: allocate 4-byte request-ID item; `0x1a6944 ldr r0,[sp,#0x44]` → `0x1a6946 str r0,[r1]`: save UHID request ID; `0x1a6948 ldr.w r0,[r10,#0x28]` → `0x1a694c bl 0x2b4280`: enqueue element.

By contrast the **SET_REPORT** branch:
- `0x1a6964 ldrb r0,[r7]`; `0x1a6970 cmp r0,#5` governs log level; `0x1a6974–0x1a6984` logs SET report type/size.
- `0x1a6988 ldrb.w r3,[sp,#0x49]`, compares report subtype against 2, 1, 0 at `0x1a698c`, `0x1a6990`, `0x1a6994`.
- For subtype zero, `0x1a6998 ldrh.w r2,[sp,#0x4a]`, `0x1a699c mov r0,r10`, `0x1a699e movs r1,#3`, then dispatches to `0x1a6a24` → `0x1a6a26 bl 0x1e15c8` with report data `[sp,#0x20]`; subtypes 1 and 2 use `0x1a6a1c`/`0x1a6a12` respectively. (The exact semantics of `0x1e15c8` and subtype mappings remain to be verified.)
- **Unlike the adjacent GET branch, the SET branch does not increment queue +0x2c, allocate a 4-byte request-ID item, read `[sp,#0x44]` or invoke the enqueue helper `0x2b4280`.** It proceeds to send report over Bluetooth without preserving the incoming UHID request ID in the observed path.

Coupled with later event-5 completion → `0x1a6fec` logging-only callback, this shows **both halves of the original M3 SET_REPORT bridge deficiency**: ingress does not perform corresponding request-ID enqueue, and completion does not issue type-14 kernel response. It is more precise than an assumption based on old AOSP source alone. **Caveats:** the body of dispatch helper `0x1e15c8` and all other potential reply writers have not been exhaustively analyzed; cannot claim that every possible alternate path is absent. Even a correct future UHID SET repair does not fix the earlier measured DS3 HCI auth failure 0x22.

No raw proprietary binary or full disassembly committed; no on-device operations, injection, SELinux change or patch authorized.

## 2026-11-01 eleventh pass: original M3 native SET_REPORT downstream helper decoded

Rechecked the actual owner-uploaded 2024 SHA-pinned `libbluetooth.so` using LLVM Thumb disassembly of **0x1e15c8–0x1e15fc**, the direct callee at `0x1a6a26` in the SET ingress path. This is not a synthetic fixture:

```asm
1e15c8: push.w {r4,r5,r6,r7,r8,lr}
1e15cc: mov r7,r0                  ; device/context
1e15ce: add.w r0,r2,#0x16         ; buffer size = report length + 22
1e15d2: mov r4,r3                  ; payload pointer
1e15d4: mov r5,r2                  ; length
1e15d6: mov r8,r1                  ; subtype/report type
1e15d8: bl 0x2b280c               ; allocation
1e15dc: mov r6,r0
1e15de: movs r0,#0xe
1e15e0: strh r0,[r6,#4]           ; internal BTA message/event field 0x000e
1e15e2: add.w r0,r6,#0x16
1e15e6: mov r1,r4
1e15e8: mov r2,r5
1e15ea: strh r5,[r6,#2]
1e15ec: bl 0x4aa9b6               ; payload copy-like helper
1e15f0: ldrb r0,[r7,#4]
1e15f2: uxtb.w r1,r8
1e15f6: mov r2,r6
1e15f8: pop.w {r4,r5,r6,r7,r8,lr}
1e15fc: b.w 0x15d4b2             ; internal Bluetooth dispatch
```

**Important numerical collision:** the internal 16-bit `0x000e` at buffer+4 is **NOT evidence of Linux `UHID_SET_REPORT_REPLY=14`**. This routine builds a Bluetooth native message and dispatches to `0x15d4b2`, rather than issuing a `write(fd, struct uhid_event,...)`. The arguments to `0x1e15c8` are device/context, mapped report subtype, length and payload pointer; the incoming kernel UHID request ID is **not supplied**. The code at `0x1a6964–0x1a6a26` likewise did not enqueue its ID. Coupled with the completed SET event-5 callback's no-op implementation, this strongly constrains where the request correlation is lost.

This finding describes the **observed standard ingress → helper path** only; a separate alternate kernel reply writer elsewhere in the stripped binary is still not exhaustively excluded. Also, the internal message's `0x000e` is in a different ABI/struct and must not be misrepresented as the kernel event type 14. Any future native bridge must introduce per-device bounded SET request bookkeeping and correlate real completion status, rather than treating a successfully queued Bluetooth message as a successful UHID transaction. HCI authentication 0x22 is an earlier independent gate.

Original OEM ELF not committed; no M3 activity, injection, firmware change, Bluetooth restart or PR merge.

## 2026-11-01: SET request correlation design — fail-closed implementation started

Original 2024 native `0x1e15fc` tail-calls `0x15d4b2`. In the verified latter function, `0x15d4b6` allocates a fixed `0x14`-byte Bluetooth command wrapper; it assigns event/command fields `0x1708` (halfword at buffer+0) and `5` (byte at buffer+8), stores the original payload pointer at buffer+0x10, and stores report subtype byte at +9. It then tail-calls `0x16b018`. **No original UHID request ID is included in this wrapper.** This is real original-ELF machine code evidence, not a claim that the downstream `0x16b018` callback has been fully decoded.

**Concurrency hazard:** the outgoing native SET completion callback (event=5) carries no UHID request ID. A naive FIFO completion matcher is unsafe if several SET_REPORTs are outstanding for a device or a late response arrives after a timeout/disconnect. Accordingly, an offline executable transaction specification has now been added:

- `experiments/m3-hid-apk/set_report_transactions.py` — one in-flight SET per device, retains exact UHID request ID and native (unmapped) status, disallows duplicate/concurrent submission, quarantines timed-out or disconnected sessions, never fabricates success.
- `experiments/m3-hid-apk/test_set_report_transactions.py` — **6 local host-only unit tests PASS**: request ID/status retention, no unsolicited reply, no parallel requests, stale timeout handling, disconnect quarantine, separate-device isolation and reset requiring external new-session verification.

**Important limitations:** this is NOT a production native bridge, Android service hook or UHID writer. Even the reset API requires an external verified guarantee that all callbacks from the prior session are drained; it is not a claim that Android provides that guarantee. The original SET completion status enumeration/errno mapping, HID host probe interaction, native queue/lifetime ownership, and rollback are still unknown. Never generate `UHID_SET_REPORT_REPLY` from this model alone, and do not infer a status=0 success from merely queueing a Bluetooth message. M3 live-injection gate remains NO_GO.

## 2026-11-01 safety correction: one-in-flight is not sufficient to prove correlation

Review of the offline model exposed a genuine safety gap: `reset_after_verified_new_session` permitted reusing the same device key after timeout/disconnect **without an enforceable native callback epoch**. Since original M3 SET completion callbacks have no UHID request ID and no generation token, an old delayed completion could be attributed to a new request. The API's name did not constitute proof.

The experimental implementation **now removes reset entirely**; a device key is permanently quarantined within that manager after timeout/disconnect. Creating a *new manager* would require independently proven isolation of the earlier callback source; no such isolation has been demonstrated in live M3. Test cases now assert no unsafe reset, deadline equality quarantine, malformed IDs, and device separation. **Even one-in-flight is not itself sufficient for production**: a stale callback after an apparently successful previous request or unexpected unsolicited callback still requires independent ordering/lifetime proof; transaction ID omission cannot be fixed by a Python state machine.

Files: `experiments/m3-hid-apk/set_report_transactions.py`, `test_set_report_transactions.py`. This is a host-only specification, not an Android native implementation, so it does not change S7-C4C injection NO_GO. Status-to-errno mapping, real Bluetooth completion guarantees, and exact downstream event lifetime are still unresolved. Do not turn a Python test pass into authorization to write UHID responses.

## 2026-11-01 twelfth pass: original callback pending-event reset and status handling

Actual owner-supplied 2024 M3 binary inspected again with `llvm-objdump -d --triple=thumbv7a --start-address=0x15ca40 --stop-address=0x15cb45`. Significant exact instructions:

```asm
15ca54: ldrh    r0, [r4, #0x1c]  ; per-device outstanding w4_evt
15ca88: cmp     r0, #5           ; SET_REPORT completion
15ca8a: strb.w  r1, [sp]         ; mapped native completion status
15ca90: uxtb    r1, r1
15ca92: mov     r0, r2          ; HID handle
15ca94: bl      0x1a6fec       ; confirmed log-only bta_hh_co_set_rpt_rsp
15cb18: ldrh    r0, [r4, #0x1c]
15cb28: blx     r2              ; separate upper-level callback
15cb2a: movs    r0, #0
15cb2c: strh    r0, [r4, #0x1c] ; clear awaited event after callback
```

The dispatcher **does** retain an outstanding event code in the device control block and clear it after reporting a completion. This is further corroborated by historical Fluoride `bta_hh_act.cc`, which invokes `bta_hh_co_set_rpt_rsp(handle,status)`, then emits the application callback and clears `p_cb->w4_evt=0` (https://android.googlesource.com/platform/system/bt/+/c110eca93d69fc336a81360fc22a1e439297f634/bta/hh/bta_hh_act.cc). But `w4_evt` is **only the event class (5 = SET_REPORT)**, not the originating kernel UHID request ID or an epoch.

**Implications:** the binary supports per-device event-type tracking, *not* proof that multiple successive SET requests cannot race, that late completion cannot arrive after `w4_evt` is reused, or that an ID-less callback can safely answer the current pending UHID request. Status `r1` is derived earlier from `[r5+0x10]` and is also passed to the upper-layer callback, but its exact status-to-UHID-error mapping has not been verified. No substitute UHID type-14 writer proven.

The fail-closed Python transaction model updated in previous turn was reproduced locally in the current runtime with its eight unit-test cases: **8/8 PASS** (host-only, not M3); previous unsafe reset API remains removed. This validates model invariants only, **NOT real native order/lifetime safety**.

For actual implementation review, first establish whether M3's native queue rejects concurrent SETs/overwrites `w4_evt`, whether a delayed completion can be misclassified after reuse, and how a detached/reconnected device invalidates old callbacks. Do not ship kernel replies from this model or interpret a simple `w4_evt` flag as a transaction ID. No M3 live changes or S7-C4C approval.

## 2026-11-01: Native pending-event setter located; concurrent SET overwrite still unresolved

Directly disassembled owner-uploaded original 2024 SHA-pinned M3 ARM32 ELF, searching its actual halfword stores and reconstructing the command dispatcher `0x15d180–0x15d288`:

- `0x15d18c ldrb r7,[r1,#8]` picks an internal command/event-type byte from command wrapper.
- `0x15d1d8 bl 0x27e684` calls a shared connection/dispatch helper, returns status in `r0`.
- If status is nonzero, `0x15d1dc cbz r0,0x15d218` **does not branch** and follows an error/event handling path. If status is zero, control branches to `0x15d218`.
- `0x15d218 ldrb r3,[r6,#8]`, `0x15d21a subs r0,r3,#4`, `0x15d21c cmp r0,#6`, `0x15d21e bhs 0x15d23a`: internal commands in the range 4..9 enter next block.
- `0x15d220 strh r7,[r4,#0x1c]`: **writes the awaited native event class to per-device `w4_evt`**. The previously proven native completion handler at `0x15ca54` reads this same field and at `0x15cb2c` clears it.

**Crucial caveat:** there is **no local compare/test of the *previous* `[r4,#0x1c]` value** immediately before this write. But `0x27e684` does have connection/channel state checks and calls an additional helper `0x27eac4`; its result gates the setter. This does **not** establish that an overlapping second SET command can reach the store, nor that Bluetooth transaction ordering is serial. Until native queue and state-machine admission are traced, pending-event **overwrite is a plausible hazard, not a demonstrated runtime bug**.

**Engineering consequences:** refuse to use `w4_evt` as a UHID transaction ID, do not claim safe FIFO order; enforce one-in-flight at the ingress boundary *before* sending native messages and require proof that legacy transport cannot emit stale callbacks against a reused session. Continue prioritizing measured HCI auth 0x22 and Java HID Host bond gate; this UHID gap is later in the path. Only offline original-ELF inspection was performed. No M3 changes, injection, security bypass, or live Bluetooth restart.

## 2026-11-01: Verified upstream status gates ahead of w4_evt setter

**Original ELF bytecode directly rechecked this turn**, SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`, using LLVM Thumb disassembly. The decisive path is:

```asm
15d1d4: mov     r1,r7
15d1d6: mov     r2,r5
15d1d8: bl      0x27e684
15d1dc: cbz     r0,0x15d218     ; only zero status takes command-accepted path
...
15d218: ldrb    r3,[r6,#8]
15d21a: subs    r0,r3,#4
15d21c: cmp     r0,#6
15d21e: bhs     0x15d23a
15d220: strh    r7,[r4,#0x1c]   ; w4_evt store for command types 4..9
```

In native helper `0x27e684`, the status/connection gate is nontrivial: `0x27e6b8` checks a bounded device index (<=6); `0x27e6cc` checks an allocated/active slot; `0x27e6da` requires a connection-state byte equal to 1, and `0x27e6ee` delegates to `0x27eac4` only if these checks pass. Helper `0x27eac4` calls `0x233a88` at `0x27eaec` to check a further per-device/channel condition; one failure branch returns 4 at `0x27eb30`. At `0x27eb00` it tests a connection/security flag bit and another failure branch returns 8 at `0x27eb40`. It also inspects command codes and constructs HID protocol packet data downstream.

**What is now proven:** `w4_evt` is written only on the zero-return acceptance branch from a real native HID command gate. The upstream path verifies device slot and state; earlier wording suggesting no guards anywhere was overly broad.

**What is not proven:** this gate does not visibly compare `w4_evt` with a prior outstanding SET transaction. `0x233a88` and downstream command queue ordering still require analysis before deciding whether overlapping SETs are rejected, serialized, or can overwrite `w4_evt`. Return codes 4 and 8 are machine-code facts, but their exact public enum names are not confirmed here. Do not elevate the lack of local `w4_evt` check into a demonstrated overwrite race or assume return 0 means the actual Bluetooth peer acknowledged a report.

The M3's earliest observed DS3 failure remains HCI authentication 0x22; the UHID SET reply gap is later in the connection path. This pass remains offline only and uses no device modifications, hooks, paired-device actions, or firmware distribution.
