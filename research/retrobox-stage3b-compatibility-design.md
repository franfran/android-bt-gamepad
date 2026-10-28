# RetroBox M3 — Stage 3B: DualShock 3 Bluetooth Compatibility Design

**Status:** Design selected; not implemented. **Date:** 2026-10-25 (America/Toronto). **Target:** M3 Android 12 / API 31, ARM32, AIC Bluetooth HAL 1.0. **Constraints:** no external dongle, no firmware flashing, preserve unrelated Bluetooth security, reversible deployment.

## Executive decision

**Selected:** extend the existing Android Fluoride/Bluedroid Bluetooth pipeline with a narrow, explicitly registered DS3 cable-pairing compatibility path. Reuse the AIC HAL, the existing Bluetooth HID host / UHID path, and RetroArch's successful wired mapping. Borrow *behavior* and protocol facts from BlueZ Sixaxis, the cable-pairing security-level work in BlueZ, and BthPS3; do not port their entire stacks or kernel drivers.

**Not yet established:** that M3's incoming DS3 ACL/L2CAP events can reach HID without conventional legacy authentication, that any single Java bond check is the only blocker, or that the current binary exposes a safe patch point. A successful HCI PIN Code Reply is not successful authentication.

## Actual device evidence and limits

- DS3 USB controller: Sony VID:PID `054c:0268`; Linux `/dev/input/event3`, Android `GAMEPAD | JOYSTICK`; RetroArch menu/remapping successful with profile device name `Sony PLAYSTATION(R)3 Controller`.
- DS3 wireless address `11:22:33:44:55:66`. Its USB master address is set to the M3 adapter `AA:BB:CC:DD:EE:FF`.
- HCI snoop: incoming legacy `PIN Code Request`; Android 6-byte PIN reply was submitted and accepted as a *host command*; `Authentication Complete` returned `0x22` LMP Response Timeout after ~30 s. Repeat attempts did not create a bond record.
- `bt_config.conf` holds adapter information only; no DS3 bond section. This is a result, not established cause.
- Android Bluetooth owned in userspace: HAL `android.hardware.bluetooth@1.0-service`, app `com.android.bluetooth`; `/sys/class/bluetooth` has no `hci0`. Successful Linux L2CAP `socket()/bind()` proves kernel interface only, not shared access to hardware traffic.
- Extracted builds: `/system/app/Bluetooth/Bluetooth.apk`, `/system/lib/libbluetooth.so`, `/system/lib/libbluetooth_jni.so`; strings and metadata found, **no proven machine-code patch address**. Reported `google/raven` fingerprint must not be treated as proof this is Pixel software.

## Proven approaches to borrow (with portability boundary)

| Reference implementation | Reusable behavior | Cannot simply transplant |
|---|---|---|
| BlueZ Sixaxis plugin | USB cable registration; device address, name/PnP ID; installed HID SDP record; trusted/cable-paired state; host-side cable pairing | BlueZ's manager, D-Bus/udev integration, storage, callbacks |
| BlueZ April 2025 cable-pairing change | Lower incoming HID L2CAP security only for cable-paired devices; retain stronger requirement for other devices | Linux `BT_IO_SEC_LOW` is **not** an Android `bt_stack.conf` switch |
| BthPS3 | Custom DS3 profile, reserved HID Control PSM `0x11` and Interrupt `0x13` handling, without OS pairing UI | Windows kernel/filter driver and Bluetooth DDI |
| USB Host Shield PS3BT | HID startup and report handling if existing Android HID host cannot deliver reports | Embedded project's HCI/controller ownership model |

Source links:
- BlueZ Sixaxis: https://kernel.googlesource.com/pub/scm/bluetooth/bluez.git/+/refs/tags/5.81/plugins/sixaxis.c
- BlueZ targeted low-security proposal: https://www.spinics.net/lists/linux-bluetooth/msg119483.html
- BlueZ updated input server: https://codegraph.jelmer.uk/bluez/5.87-2/profiles/input/server.c
- BthPS3: https://github.com/nefarius/BthPS3
- Android native legacy PIN handling: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/9194524a92/system/stack/btm/btm_sec.cc
- Android HID Host (reference, may differ from M3): https://android.googlesource.com/platform/packages/apps/Bluetooth/+/refs/heads/master/src/com/android/bluetooth/hid/HidHostService.java

## Preferred architectural modification points

**A. Registration before wireless attempt (USB trusted bootstrap).** A system-privileged registration function receives a USB-confirmed DS3 identity, its Bluetooth address, Sony VID/PID, and M3 local address; persists an *allowlist with physical USB-proven enrollment*. It does **not** invent a Bluetooth LinkKey, nor blindly trust device name alone. The registration must be revocable and bound to the local adapter's address. Existing sixpair host-MAC writing may remain an onboarding step.

**B. Native Bluetooth security and incoming ACL/L2CAP behavior.** In M3-specific Fluoride security-manager/HID input path, find the exact branch that upgrades DS3's inbound connection into conventional PIN/bonding and/or requires encryption before allowing HID Control/Interrupt. Implement an explicitly allowlisted cable-paired exception scoped to correct HID service + addresses, only where necessary; preserve ordinary security for every other device. **Do not automatically suppress all PIN challenges based solely on VID or Bluetooth name.** If firmware insists on authentication before L2CAP can proceed, a HID-only authorization exception will not resolve `0x22`; confirm the state transition in instrumented testing.

**C. HID host acceptance.** Verify actual M3 APK bytecode for the inbound bonded-device check before changing it. An exception may be required for the same cable-paired DS3 identifier. This is downstream of transport authentication and cannot fix the timeout by itself.

**D. Input handoff.** Prefer existing Fluoride HID host -> Android input device (`/dev/uhid` or existing platform pipeline). Add custom report parsing only if HID input cannot initialize. RetroArch should consume `GAMEPAD | JOYSTICK`; controller profile may need wireless input name/VID:PID match but no emulator source change.

## Candidate options (ranked)

1. **AOSP-based Bluetooth stack rebuild / controlled overlay with DS3-scoped native and Java hooks (preferred engineering path).** Precise source match and build/ABI verification required; significant but contained scope.
2. **In-process instrumentation for testing only** (if root injection mechanism and Android security constraints can be safely understood): instrument state transitions before making permanent changes; no indiscriminate binary patch, no assumptions that root implies straightforward hooking.
3. **USB fallback** (already works) if security/firmware prevents narrowly scoped solution.

Rejected: generic PIN guessing; editing `bt_config.conf` to manufacture bond/key; global auth downgrade; unmodified `sixad` / BlueZ daemon on HAL-owned UART; porting BthPS3 Windows kernel driver; directly replacing `/system/lib/libbluetooth.so` without recovery plan.

## Stage 3C — concrete validation gates

**Gate 1 — source mapping, offline.** Decompile `Bluetooth.apk` and inspect incoming HID path. Disassemble M3 `libbluetooth.so` around *actual* references/call sites for `btm_sec_pin_code_request`, HCI auth-complete and HID security request. Identify matching Android 12 source revision, branch predicates, required data structures and library ABI. No deployment until these are verified.

**Gate 2 — observe specific rejection without global changes.** Establish trace points: ACL connected, PIN request, auth/LinkKey state, incoming HID Control/Interrupt PSM routing, HID host service decision. Confirm whether the relevant rejection is before or after PIN request. HCI snoop plus instrumented native logs need to agree.

**Gate 3 — DS3 allowlist bootstrap.** Build separate provisioning/test control handling USB-verified DS3 address and M3 adapter, secure registration, add/remove capability, and strict no-effect for unknown peripherals.

**Gate 4 — limited transport PoC.** With explicit rollback, test a single Sony DS3: PS button with USB disconnected; Bluetooth ACL persists >30s; Control/Interrupt connection established; first HID report received. Report failure codes and exit cleanly on mismatches.

**Gate 5 — Android input.** `dumpsys input` indicates `GAMEPAD | JOYSTICK`, and button changes arrive; RetroArch menu works. Later test second DS3 and reconnect across reboot. Verify other Bluetooth device behavior unchanged.

## Rollback and safety prerequisites

- Keep pristine extracted APK/SO copies and checksums; preserve `bt_config.conf` and HCI logs privately (do not publish keys or MAC addresses).
- **Before any overlay or stack binary replacement**, establish independent ADB root access after Bluetooth service failure, boot-time recovery/auto-disable, and a reversible method verified without touching permanent partitions.
- Disable full HCI snoop after debugging; use restrictive log permissions.
- Scope exception to deliberately USB-enrolled DS3 devices and only incoming HID PSMs; never trust names alone, and never turn off global Bluetooth security.
- Do not edit signed system packages or change SELinux/permanent partitions as a speculative first step.

## Completion definition

Stage **3B completed as design**, not functional Bluetooth implementation. Stage **3C Gate 1** is the next actionable engineering task; it should produce exact control-flow evidence and a scoped test strategy, not another generic socket capability probe. Current M3 can play with wired DS3. Wireless DS3 is **not connected yet**.
