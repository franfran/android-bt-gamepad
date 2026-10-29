# S8-A — DS3 wired USB baseline (non-invasive owner test)

## Rationale

S7's owner-controlled independent ARM32 loader is **not** discarded. The blocked item is live Bluetooth injection, not the controller or the loader prototype. The first S8 target is to separate Android input compatibility from wireless transport without touching `com.android.bluetooth`.

## Safety boundary

Owner physically connects the DS3 over a **known-good USB data cable** to an M3 USB host/OTG port. No root-only writes, Bluetooth service restart, pairing changes, `setprop`, `uinput` creation, SELinux change, or module loading. Ensure M3 remains powered as intended and has an ordinary Wi-Fi ADB connection. USB used by DS3 may compete with USB-ADB transport: use Wi-Fi ADB.

## Runbook

**Before plugging in** (Mac terminal; substitute the current ADB serial):

```sh
adb -s 192.168.1.17:1080 shell input --help
adb -s 192.168.1.17:1080 shell dumpsys input
```

`input --help` is optional and not a DS3 test; omit it if output is unwieldy. Save or inspect `dumpsys input` **locally**; it may expose unrelated names and device identifiers. Do not paste full dumps into public issues.

**Connect DS3 over USB; do not press a pairing-reset sequence.** Read the current Android input device inventory:

```sh
adb -s 192.168.1.17:1080 shell dumpsys input
```

Check for a newly appearing input device with DS3/Sony identifiers, joystick/gamepad sources and axes/buttons. Some kernels expose USB device details without creating Android input devices. If a USB device appears but not an Android InputDevice, record **USB_ENUMERATED_ONLY**; do not treat it as input success.

**UI test:** Open RetroArch normally, navigate using the controller (not via `adb shell input`). Check D-pad, four face buttons, shoulder buttons, both analog sticks and Start/Select. If RetroArch cannot navigate, check Android's normal gamepad/input configuration before drawing a Bluetooth conclusion. Avoid pressing combinations that reset controller association.

## Evidence worksheet — share only these observations

```json
{
  "stage": "S8-A",
  "mode": "OWNER_USB_BASELINE",
  "usb_physical_connection": "CONNECTED_OR_NOT",
  "new_android_inputdevice_visible": "YES_NO_UNKNOWN",
  "retroarch_ui_navigation": "YES_NO_UNTESTED",
  "dpad": "PASS_FAIL_UNTESTED",
  "face_buttons": "PASS_FAIL_UNTESTED",
  "analog_sticks": "PASS_FAIL_UNTESTED",
  "shoulders": "PASS_FAIL_UNTESTED",
  "start_select": "PASS_FAIL_UNTESTED",
  "observations": "sanitized short note"
}
```

Never include raw `dumpsys` payload, MAC address, serial, private file path, or human account identifiers. If ADB connection is lost, disconnect the controller normally and return to ordinary baseline; do not modify Bluetooth or Android configuration to recover.

## Decision rule

- **USB_INPUT_PASS** only if Android exposes a matching device **and** the controller operates in RetroArch (controls tested).
- **USB_ENUMERATED_ONLY** if the USB layer sees hardware but Android input doesn't.
- **USB_UNKNOWN** if visibility or UI cannot be established.
- **USB_NOT_WORKING** if the controller is detected but expected actions are reproducibly absent.

A successful USB baseline reduces uncertainty around Android input delivery, but Bluetooth transport and add-on linker namespace remain **UNVERIFIED**. S7-C4C-3 live injection remains **PAUSED / NO-GO**.

## Next engineering move

If USB input passes, evaluate a disposable Linux DS3 wireless receiver and an **independently authorized** Android input handoff, with release-on-disconnect and bounded input rates. If USB fails, first resolve USB host/input support rather than engineering a Bluetooth bridge around an unproven input sink.
