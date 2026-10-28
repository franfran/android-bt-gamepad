# RetroBox DS3 Pairing Diagnostic v0.2

Experimental Android 12 (API 31+) Bluetooth Classic diagnostic / **one-shot** legacy PIN test for iMETBOX M3.

## Scope and safety

- Target controller **only**: `11:22:33:44:55:66`.
- M3 Bluetooth host address **hardcoded**: `AA:BB:CC:DD:EE:FF` (previously read from the box). **Do not use on a different adapter without updating it.**
- Default: **DIAGNOSTIC ONLY**. No PIN sent.
- Manually arm **one** attempt, valid for **60 seconds** while app stays foreground; consumed even if `setPin()` fails.
- PIN options are **experiments**, NOT known-good DS3 PINs: binary six-byte host address `B0 A7 AB 64 EE 4F`, or ASCII `0000` (`30 30 30 30`). Do not confuse binary host MAC with ASCII MAC address.
- `setPin()` true only means the request was accepted, not that authentication succeeded. Stock Android pairing UI might race with this helper.
- No root, firmware changes, broadcast abortion, persistent background services, or changing bonded device data.

## Build (Mac)

From repository root:

```sh
export JAVA_HOME=/opt/local/Library/Java/JavaVirtualMachines/openjdk17/Contents/Home
export ANDROID_HOME="$HOME/Library/Android/sdk"
/opt/local/bin/gradle :app:assembleDebug
```

APK: `app/build/outputs/apk/debug/app-debug.apk`.

## Test

```sh
DEVICE=192.0.2.10:1080
adb -s "$DEVICE" install -r app/build/outputs/apk/debug/app-debug.apk
adb -s "$DEVICE" shell am start -n city.retrobox.ds3diagnostic/.MainActivity
adb -s "$DEVICE" logcat -c
```

Grant Bluetooth permission. Keep helper in foreground. For a controlled first test tap **ARM NEXT REQUEST: HOST MAC (6 raw bytes)** and press PS promptly. Do not select another mode unless you intend a separate attempt. Allow bonding to finish, then:

```sh
adb -s "$DEVICE" logcat -d -s RetroBoxDS3:I '*:S'
adb -s "$DEVICE" shell cat /proc/bus/input/devices
```

Look for `PIN_ATTEMPT`, `SET_PIN_RESULT`, and `BOND_STATE ... BONDED`, then HID input device registration. Bluetooth bonding and HID input are separate stages.

## Limitations

This app is only registered while its Activity is open. Android 12 broadcast delivery and security enforcement may still prevent `setPin()` from succeeding on some firmware. `PAIRING_VARIANT_PIN` has been directly observed on the user's M3 using v0.1. No confirmed successful DS3 pairing yet. Pairing might require a different algorithm from either offered experimental PIN.
