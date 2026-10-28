# RetroBox DS3 — Stage 3C Gate 1: Binary Control-Flow Audit

**Scope:** Offline static audit of M3's extracted Android 12 native Bluetooth libraries. **Status:** Partial gate completion — disassembly verified; exact DS3 authentication/security branch not yet established. **Device changes:** None.

## Inputs and identity

- M3: Android 12, API 31, ARM 32-bit, `com.android.bluetooth`.
- `libbluetooth.so` SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`.
- `libbluetooth_jni.so` SHA-256 `1db644b6e2203431e95d55d420729db054fa7f2f8e0bd2f8cbd35a00abf17dfd`.
- Relevant HCI test: PIN Code Request followed by successful **HCI command completion** for PIN Code Request Reply, then authentication timeout `0x22` after ~30 seconds; **no link key established**. Command success does *not* prove authentication success or the PIN's correctness.

## Verified ELF mapping (libbluetooth.so)

- Architecture: `ELF32 ARM EABI5`, Android 31, stripped.
- `.rodata`: file offset and VMA `0x5fd30`, size `0xb9600`.
- `.text`: file offset `0x119e50`, VMA `0x11ae50`, size `0x4c3fd8`.
- The executable contains Thumb-2 code. Forcing ARM decoding at `.text` start produces nonsensical instructions; **use Thumb decoding**. Example starting at VMA `0x11ae60`: `push {r4,r5,r6,lr}`, `sub sp,#0x10`; a direct call (`bl`) appears at `0x11ae8c`.
- Because `.rodata` is within the initial LOAD and has identical file offset/VMA, string offset `0x687a8` is also its static VMA, but **not an executable address**.

### Verified diagnostic strings

| String | File offset / VMA | Meaning |
|---|---|---|
| `btm_sec_pin_code_request bonding sending reply` | `0x687a8` | An available debug message, not proof a specific branch executed. |
| `btm_sec_auth_complete` | `0x68789` | An available debug label. |
| `btm_sec_link_key_request` | `0x7c50f`, `0x971c7` | Two string occurrences. |
| `btm_sec_l2cap_access_req_by_requirement` | `0x89dc3` | An available debug label. |

## Verified JNI point

`libbluetooth_jni.so` exports `android::register_com_android_bluetooth_hid_host(JNIEnv*)` as an ARM Thumb function at **VMA `0x2cfbc`** (`readelf -Ws`, low bit indicates Thumb). Disassembly starting at `0x2cfbc` shows a valid function prologue and JNI virtual calls. This validates the JNI wiring but **does not make JNI the cause** of the authentication failure.

## AOSP correspondence

- Android Bluetooth's native security manager implements `btm_sec_pin_code_request`, `btm_sec_auth_complete`, and PIN callback support (AOSP `system/bt/stack/btm/btm_sec.cc`).
- Relevant maintained source for comparison: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/f4e439c22354f0aa868a982bc88bcc9de3bc37f7/system/stack/btm/btm_sec.cc (newer branch; behavior illustrative, **not necessarily identical** to M3).
- Android 12 historical header: https://android.googlesource.com/platform/system/bt/+/refs/heads/android12L-d2-s8-release/stack/btm/btm_sec.h.
- Matching a debug message to source semantics does not establish an exact machine-code patch site in the stripped M3 binary.

## Current architectural inference

1. Native security authentication happens before a useful Android HID input device appears. Relaxing a Java HID Host bond requirement **alone** is insufficient evidence of a fix.
2. Stage 0–2 Linux L2CAP socket bind tests succeeded, but `/sys/class/bluetooth` did not expose `hci0`; Android HAL `android.hardware.bluetooth@1.0-service` owns the transport. No evidence kernel L2CAP sockets receive the controller's packets. **Do not build a Linux socket listener as the primary path.**
3. DS3-specific cable-pairing remains a promising design, but implementing it in Android Fluoride involves native authentication / L2CAP policy and potentially the HID Host; it is **not** a safe one-byte patch inferred from an AOSP code snippet.

## Gate 1 outstanding tasks

1. Obtain full targeted Thumb-2 call-graph / xrefs to diagnostic strings inside stripped `libbluetooth.so` (e.g. Ghidra or equivalent); identify enclosing native security functions and branch predicates.
2. Decompile the **extracted M3 Bluetooth.apk**, not just use an arbitrary Android release, and document any HID Host bond-state guard in its exact bytecode.
3. Build an isolated offline test for the DS3-scoped policy. Require source-level patch review and a reversible runtime/boot overlay before modifying M3's Bluetooth service.
4. Record expected event transitions and rollback: unmodified DS3 pairing fails as before; modified flow should show established authenticated or permitted transport (without global weakening), HID input registration, and restoration after removing the patch.

**Gate 1 verdict: INCOMPLETE.** Exact auth callsite and safe patch point remain unverified. No operational patch supplied and no device changes required.
