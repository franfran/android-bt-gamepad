# RetroBox M3 — DS3 wireless native PoC, stage 0

## Scope

Objective: connect an original Sony DualShock 3 (USB VID:PID `054c:0268`) wirelessly to the iMETBOX M3 (Android 12, AOSP/Fluoride Bluetooth stack, vendor AIC Bluetooth UART `/dev/ttyAS1`). This is **not yet a pairing implementation**. The current first milestone is a non-invasive native capability probe, to select a technically viable implementation path before touching the system Bluetooth process.

Evidence already established by device testing:
- DS3's stored master MAC was set by `sixpair` to M3 `AA:BB:CC:DD:EE:FF`.
- M3 receives incoming Bluetooth connection from DS3 `11:22:33:44:55:66`.
- HCI PIN Code Request Reply was transmitted, but authentication failed after about 30 seconds with `0x22` (LMP Response Timeout).
- Android keeps no bonded DS3 record in `/data/misc/bluedroid/bt_config.conf`.
- DS3 works over USB (`event3`), Android sees GAMEPAD + JOYSTICK, and RetroArch `com.retroarch.ra32` works after adding the DS3 Android autoconfig profile.

## Build from macOS (Android NDK installed)

```bash
export ANDROID_HOME="$HOME/Library/Android/sdk"
NDK="$ANDROID_HOME/ndk/26.3.11579264"
# Change NDK above if your installed NDK differs; `ls "$ANDROID_HOME/ndk"`.
CLANG="$NDK/toolchains/llvm/prebuilt/darwin-x86_64/bin/armv7a-linux-androideabi21-clang"
"$CLANG" -Os -Wall -Wextra -o l2cap_probe l2cap_probe.c
file l2cap_probe
```

On Apple Silicon macOS, the NDK prebuilt toolchain directory commonly remains `darwin-x86_64`; check your actual installed layout first.

## Run on M3 (read-only; no Bluetooth toggle required)

```bash
DEVICE=192.0.2.10:1080
adb -s "$DEVICE" push l2cap_probe /data/local/tmp/l2cap_probe
adb -s "$DEVICE" shell su 0 chmod 755 /data/local/tmp/l2cap_probe
adb -s "$DEVICE" shell su 0 /data/local/tmp/l2cap_probe
```

Interpretation:
- `AVAILABLE` for L2CAP socket creation indicates a Linux Bluetooth socket API is exposed to this process. **It does not prove** fixed PSM bind/listen, Bluetooth ACL/authentication interoperability, or coexistence with Android's Bluetooth daemon.
- `EAFNOSUPPORT` / `EPROTONOSUPPORT`: socket family or protocol not available to the process/kernel.
- `EACCES` / `EPERM`: access may be denied by UID/capabilities/SELinux. The tool prints the actual errno.

Do not attempt to independently open `/dev/ttyAS1` while the vendor Bluetooth HAL owns it, and do not patch device bonding databases without understanding the precise protocol.

## Implementation decision after probe

1. If Classic L2CAP sockets exist, investigate whether the Android Bluetooth stack exposes ACL transport to the kernel socket interface or if they use separate internal layers. Determine if port bindings and HID security can coexist **without disabling the system stack**. This is only feasibility research, not yet a recommended running service.
2. If sockets are absent/incompatible, reuse mature DS3 protocol parsing from USB Host Shield / sixaxis-android but integrate at an Android Bluetooth stack boundary. This likely requires a targeted system component or vendor-dependent access, not only an APK.
3. For input registration, investigate `/dev/uhid` using a tested Sony report descriptor / parser, or `/dev/uinput` with mapped gamepad keys/axes. Validate with `dumpsys input`; then RetroArch uses an Android autoconfig profile if needed.

## Implementation constraints

- No extra hardware, no firmware flashing, don't replace Android Bluetooth service without a rollback route.
- Controller-specific scope only; avoid globally lowering Bluetooth security.
- One DS3 and first wireless button event are the initial success criteria; two controllers later.

## Relevant source references

- Android Bluetooth stack architecture: https://source.android.com/docs/core/connect/bluetooth
- Android HID host framework (Android 12): https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android12-d1-release/core/java/android/bluetooth/BluetoothHidHost.java
- AOSP HidHostService bonding checks: https://android.googlesource.com/platform/packages/apps/Bluetooth/+/087d9f6a72a7f5ade938c2cbfb23aa01198bb85f/src/com/android/bluetooth/hid/HidHostService.java
- Existing Android/BlueZ DS3 code: https://github.com/mcherri/sixaxis-android
- Mature DS3 protocol source: https://github.com/felis/USB_Host_Shield_2.0
- Android UHID infrastructure: https://android.1.googlesource.com/platform/frameworks/base/+/refs/heads/android12-mainline-captiveportallogin-release/cmds/hid/
