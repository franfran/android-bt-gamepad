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
