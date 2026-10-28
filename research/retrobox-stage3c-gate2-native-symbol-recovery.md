# RetroBox M3 — Stage 3C Gate 2: native symbol recovery and HID authentication callsite

Date: 2026-10-25. Input: user-supplied M3 `/system/lib/libbluetooth.so` (Android 12/API 31, ARM32, stripped, ELF BuildID `0d29a62178e43066e018216c1f1d5b18`). All operations were offline. **No system patch was built or deployed.**

## New, reproducible finding

Although the production ELF is nominally stripped, it contains an XZ-compressed **`.gnu_debugdata` mini-debug ELF**. Decoding this section reveals a symbol table with native function names, addresses and sizes. This substantially improves on the previous log-string-only investigation; avoid guessing functions from nearby strings.

Recovery with the standard `readelf` section offset `0x5fed51` and size `0x60234`:

```python
from pathlib import Path
import lzma
b = Path('libbluetooth.so').read_bytes()
Path('libbluetooth.debugdata.elf').write_bytes(
    lzma.decompress(b[0x5fed51:0x5fed51 + 0x60234]))
```

Verify locations dynamically using `readelf -SW libbluetooth.so` if using a different binary. The section offset above applies **only** to the supplied M3 library.

```sh
readelf -Ws libbluetooth.debugdata.elf | c++filt | grep -E 'hidh_l2cif_connect_ind|hidh_conn_reg|btm_sec_mx_access_request|btm_sec_l2cap_access_req_by_requirement|btm_sec_auth_complete|btm_sec_pin_code_request'
```

| Identified native function | Symbol address (Thumb bit set) | Size (bytes) | Code start (Thumb bit cleared) |
|---|---:|---:|---:|
| `hidh_conn_reg()` | `0x27e749` | 232 | `0x27e748` |
| `hidh_l2cif_connect_ind(...)` | `0x27ee29` | 720 | `0x27ee28` |
| `hidh_l2cif_connect_cfm(...)` | `0x27f0f9` | 436 | `0x27f0f8` |
| `btm_sec_l2cap_access_req_by_requirement(...)` | `0x258735` | 1564 | `0x258734` |
| `btm_sec_mx_access_request(...)` | `0x2590a9` | 1904 | `0x2590a8` |
| `btm_sec_auth_complete(...)` | `0x25b5c5` | 1412 | `0x25b5c4` |
| `btm_sec_pin_code_request(...)` | `0x25d7a1` | 896 | `0x25d7a0` |

Addresses here are ELF **virtual addresses**, not raw file offsets. Actual runtime addresses include ASLR load bias. They must not be used as patch offsets.

## Direct instruction evidence

Disassemble with explicit **Thumb** architecture; generic `llvm-objdump -d` incorrectly decodes many instructions as ARM instructions:

```sh
llvm-objdump -d --triple=thumbv7-linux-androideabi \
  --start-address=0x27ee28 --stop-address=0x27f0f8 libbluetooth.so
```

At `0x27ee28`, the recovered `hidh_l2cif_connect_ind` begins with a Thumb-2 `push.w` function prologue. This validates the symbol's placement within executable code. Multiple `bl` and `blx` sites are present, but a **complete resolved call graph is not yet established**, particularly indirect calls and wrapper functions. Do not treat every `bl` destination printed by stripped-ELF objdump as a correctly named function: its annotation may use an unrelated nearest surviving exported symbol.

## AOSP reference: likely path (not yet proven as an exact M3 call graph)

Source: Android Fluoride HID Host (`stack/hid/hidh_conn.cc`) registers both `HID_PSM_CONTROL=0x11` and `HID_PSM_INTERRUPT=0x13` with `BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT`. Older AOSP source also shows inbound HID Control processing entering `hidh_l2cif_connect_ind` and calling `btm_sec_mx_access_request(..., HID_PSM_CONTROL, ...)`, then passing the result to a security callback. On failure, the callback returns an L2CAP security block response.

References:
- https://android.googlesource.com/platform/system/bt/+/26a2ba137faf2f9b686c157e73593dbe577908c4/stack/hid/hidh_conn.cc
- https://android.googlesource.com/platform/system/bt/+/911d1ae03efec2d54c3b1b605589d790d1745488/stack/hid/hidh_conn.cc
- https://android.googlesource.com/platform/system/bt/+/e8dea68f6a0116d25ab233921030d44a99ab1b58/stack/btm/btm_sec.cc

HCI capture already confirmed inbound HID Control L2CAP connection request, followed by host `Authentication Requested`, then Link Key Request, negative reply, PIN Request, reply, and `0x22` timeout. The AOSP path is **consistent** with the capture, but this report does not claim that every AOSP branch is byte-for-byte identical to this M3 vendor binary.

## Recommended minimal patch design (research only)

1. Trace `hidh_conn_reg` security registration, `hidh_l2cif_connect_ind` and its security callback to `btm_sec_mx_access_request`, using recovered symbols and proper Thumb disassembly. Validate direct-call targets *and* indirect calls.
2. Determine exact decision point that raises incoming HID Control's authentication requirement, and separately the Interrupt channel security requirement.
3. Design a device-specific, **USB-authorized** exception with proof of prior physical pairing, not merely matching Sony vendor ID / Bluetooth device name. Never globally disable Classic Bluetooth authentication.
4. Then determine whether downstream Android `HidHostService.okToConnect()` must also accept the explicitly authorized DS3. This is separate from link authentication.
5. Deliver a reversible runtime experiment with an independent rollback path; do not replace `/system/lib/libbluetooth.so` based on symbol addresses alone.

## Actual gate status

**Achieved:** native symbol recovery and executable function starts, replacing imprecise string-based mapping.

**Not achieved:** full validated security call graph; DS3-specific authentication exception; running Bluetooth connection; safe deployable patch.

**Next concrete task:** static function-by-function control-flow reconstruction from the now recovered symbol table, especially resolving the HID security callback and `btm_sec_mx_access_request` callsite. This can be performed offline from the already supplied ELF and APK; no new device logs are necessary.
