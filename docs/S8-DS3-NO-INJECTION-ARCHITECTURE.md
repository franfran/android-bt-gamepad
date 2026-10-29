# S8 — DualShock 3 support without live Bluetooth process injection

**Date:** 2026-10-29  
**Status:** architecture selection / documentation only  
**Predecessor:** S7-C4C-3 decision review (PR #21), which remains PAUSED / NO-GO for live Bluetooth service modification.

## Product objective

Enable an original Sony DualShock 3 (Sixaxis) gamepad to function as an Android/RetroArch input device on an owner-controlled Android 12 ARM32 iMETBOX M3, without attaching to, restarting, or injecting a library into `com.android.bluetooth`.

### Important protocol split

DS3 is *not* a generic modern BLE GATT controller. Its Bluetooth mode uses legacy Bluetooth Classic HID expectations and a controller/host-address association convention. A successful Linux/BlueZ pairing mechanism should not be assumed portable to Android's Bluetooth stack.

The host needs two separate successes: (1) establish a valid transport / pairing for DS3; (2) deliver usable button/axis events to the Android input framework or RetroArch. Merely creating `/dev/uinput` events does not solve Bluetooth transport; merely pairing does not guarantee usable input events.

## Architecture candidates

| Option | Benefit | Key blockers | Stage recommendation |
| --- | --- | --- | --- |
| A. USB HID to Android input | Simplest, bypasses Bluetooth entirely; tests controller and game compatibility | OTG role, kernel HID support or app USB permission, controller initialization | **First practical baseline** |
| B. External Linux Bluetooth bridge -> Android input over trusted link | No M3 Bluetooth stack mutation; Linux host handles DS3 pairing/Classic HID, M3 needs a separately authorized input sink | Requires a second device, pairing host address setup, input injection interface / permissions, latency and reconnect behavior | **Preferred wireless alternative to prototype on disposable hardware** |
| C. Android standard Bluetooth pairing without injection | No process modification and potentially best end-user experience | DS3 legacy pairing behavior / OEM Bluetooth HID Host support uncertain; compatibility needs owner observations | **Investigate only via normal UI / existing logs; no service intervention** |
| D. Independent Bluetooth daemon sharing M3 radio | Potentially local wireless path | HCI/radio ownership conflict, Android stack coexistence, permissions and reliable recovery | **NO-GO on live M3** |
| E. Kernel / vendor Bluetooth stack modifications | Deep protocol integration | ROM/kernel build, signature/boot/recovery and high device-brick risk | **Out of scope** |
| F. Restart/ptrace/inject into `com.android.bluetooth` | Reuses built-in radio stack | Existing C4C-3 namespace and recovery gates remain unproven | **PAUSED/NO-GO** |

## Feasibility checks in order

**S8-A USB baseline (owner-controlled, normal operation only):**
1. On a disposable/known-working host first, confirm original DS3 USB VID/PID and wired input events. Never assume clones behave identically.
2. On M3, if owner later chooses, test ordinary USB-OTG controller detection without root modifications or Bluetooth changes; confirm whether Android emits `InputDevice`/RetroArch events.
3. If USB works, record button/axis mapping and latency as a baseline for any future wireless solution.

**S8-B external bridge (disposable Linux host first):**
1. Validate Linux DS3 pairing and data path with Bluetooth radio belonging to the *external host*, not M3. Setting the DS3 host address is an explicit controller-side write; obtain owner consent first.
2. Design a narrowly scoped input packet protocol, bounded rate, per-session authentication, replay protection and disconnected state = release all keys.
3. Keep Android input delivery as a separate permission/feasibility gate. A normal app cannot be assumed to inject arbitrary global input events; `uinput` and other privileged routes must be researched and independently reviewed before using them.
4. Benchmark input latency, reconnect, button hold release, and Android/RetroArch mapping; no simultaneous M3 Bluetooth daemon conflict.

**S8-C OEM native pairing:** Evaluate only non-mutating app capability and user-mediated pairing; the presence of JNI/8 dependencies does not make DS3 HID behavior supported.

## Reference evidence and limits

- Linux kernel `hid-sony` handles DS3 Sixaxis USB and Bluetooth variants, including controller Bluetooth address recognition: https://android.googlesource.com/kernel/common/+/refs/heads/android-mainline/drivers/hid/hid-sony.c
- `sixaxis-android` historical BlueZ-based approach notes it is **not** directly supported with newer Android BlueDroid implementations: https://github.com/mcherri/sixaxis-android/blob/master/README.md
- Legacy DS3 connection requires special host association in common Linux pairing flows; treat host-address writing as separate owner-approved hardware action, not a routine read-only check: https://gist.github.com/al3rez/82e49bde55d4b27cb1a4bd1682490c71

These are reference architectures, **not** validation of the current M3 firmware.

## Explicit stop / acceptance gates

- No live `com.android.bluetooth` restart, attach, native loading, radio ownership conflict, SELinux modification or kernel replacement is authorized.
- All C4C-3 NO-GO constraints remain unchanged.
- Any test writing DS3 controller Bluetooth host information or privileged Android input events requires an explicit, separately scoped owner decision.
- The next milestone should yield one of: **USB baseline proven**, **external bridge feasible on disposable host**, or **route rejected with a concrete blocker**, rather than another Bluetooth `/proc/maps` inventory.

## Recommendation

Prioritize **S8-A USB baseline**, and in parallel document **S8-B external bridge** as the preferred wireless fallback. Keep **S8-C ordinary OEM pairing** only as an opportunistic compatibility route. No implementation may claim DS3 wireless support from static research alone.
