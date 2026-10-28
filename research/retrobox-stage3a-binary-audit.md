# RetroBox M3 — DS3 Bluetooth Stage 3A: Binary audit

**Status:** Offline inspection completed; no binary modifications and no live DS3 Bluetooth connection attempted.

## Inputs / identification

- M3: Android 12 / API 31, 32-bit ARM; `com.android.bluetooth` APK at `/system/app/Bluetooth/Bluetooth.apk`.
- Bluetooth HAL: `android.hardware.bluetooth@1.0-service`; native stack `/system/lib/libbluetooth.so`; JNI `/system/lib/libbluetooth_jni.so`.
- The reported `google/raven` build fingerprint cannot be used to infer a matching Google Bluetooth implementation; rely on extracted binaries.
- Known DS3 device: Sony VID `054c`, PID `0268`, Bluetooth `11:22:33:44:55:66`; host adapter `AA:BB:CC:DD:EE:FF`.

## Reproducibility

| File | SHA-256 |
|---|---|
| `libbluetooth.so` | `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85` |
| `libbluetooth_jni.so` | `1db644b6e2203431e95d55d420729db054fa7f2f8e0bd2f8cbd35a00abf17dfd` |

Both ELF files are **32-bit ARM EABI5 shared libraries**. `libbluetooth.so` has a mapped `.text` segment and `.rodata` segment but no useful exported dynamic symbol for the internal `btm_sec_pin_code_request` / `btm_sec_auth_complete` functions. **Do not treat a string offset as a machine-code patch address.**

## Confirmed evidence (M3)

1. Wireless pairing requests reach Bluetooth Classic HCI; incoming `PIN Code Request` is generated.
2. Prior snoop trace shows a 6-byte host-MAC `PIN Code Request Reply` acknowledged at the HCI command level; it does **not** establish completed Bluetooth authentication.
3. Authentication subsequently times out (`0x22`, LMP Response Timeout); no bond is saved in `/data/misc/bluedroid/bt_config.conf`.
4. Android Bluetooth HAL and Fluoride are running; `/sys/class/bluetooth` had no kernel HCI adapter. Linux L2CAP socket bind-only tests succeeded but do not show access to the HAL-owned controller data path.
5. Wired DS3 functions as Android gamepad, including RetroArch menu and button remapping after adding its matching autoconfig profile.

## Relevant inspected native *string* locations

All values below are **file offsets of literal strings**, not instruction locations or proof of runtime execution.

| String | File offset (`libbluetooth.so`) |
|---|---|
| `btm_sec_pin_code_request bonding sending reply` | `0x687a8` |
| `btm_sec_auth_complete` | `0x68789` |
| `btm_sec_link_key_request` | `0x7c50f`, `0x971c7` |
| `btm_sec_link_key_notification` | `0x6bc3e`, `0x9d845` |
| `btm_sec_l2cap_access_req_by_requirement` | `0x89dc3` |
| `BTM_SecAddDevice` | `0x684b3` |

These strings establish that the binary contains logging / metadata related to security handling; they **do not prove** which branch is responsible for the DS3 failure or an appropriate binary patch.

## AOSP code reference points (not yet binary-matched)

- Android `system/bt` `stack/btm/btm_sec.cc` — PIN request, PIN reply, authentication, link key, L2CAP access security checks.
  - https://android.googlesource.com/platform/system/bt/+/refs/heads/android12L-d2-s8-release/stack/btm/btm_sec.h
  - https://android.googlesource.com/platform/system/bt/+/26a2ba137faf2f9b686c157e73593dbe577908c4/stack/btm/btm_sec.cc
- Bluetooth HID Host service bond checks need comparison against **this** M3 APK's exact implementation before considering any exception. Newer AOSP branch behavior alone is not proof of the M3 code path.
- DS3 third-party implementations show that USB host-MAC programming is only one part of cable pairing. Successful USB operation or accepted HCI PIN reply alone does not establish a working Bluetooth path.

## Candidate engineering approach

1. **Do not alter firmware, `/system/lib/libbluetooth.so`, `/system/app/Bluetooth/Bluetooth.apk`, or `bt_config.conf` yet.** No established patch site or rollback mechanism exists.
2. Decompile `Bluetooth.apk` to locate actual M3 `HidHostService` incoming connection / `BondStateMachine` path; compare against Android 12 source without extrapolating from current Android head.
3. Match `libbluetooth.so` code to Android 12 source by analyzing `.text` cross-references to the literal strings and function call graph. A direct binary patch is appropriate only after the exact branches, instruction offsets, and rollback procedure are documented.
4. Borrow the **DS3 cable-pairing lifecycle** from working implementations rather than searching for arbitrary PINs. Validate whether authorization can be performed safely via a privileged, DS3-scoped service or whether the native security manager requires changes. Do not globally disable authentication.
5. Prefer a reversible test mechanism such as a separately bootstrapped process or a boot-time overlay with automatic rollback; production system library replacement is a last resort and must not be attempted without a recovery path.

## Required pass criteria for the subsequent PoC

- After a PS-button press with USB disconnected, the DS3 establishes stable wireless Bluetooth transport and continues beyond 30 seconds.
- `dumpsys input` exposes a `GAMEPAD | JOYSTICK` Android input device (or equivalent platform sources), and `getevent`/input observation shows changing button states.
- RetroArch receives inputs via the working profile or a variant using the wireless device name; this is separate from simply observing a Bluetooth `Connected` notification.
- Other Bluetooth pairing behavior is unchanged, and removal of the compatibility component restores original behavior.

## Current verdict

**Stage 3A establishes a concrete source-code investigation map but not a verified DS3 authentication patch.** The most informative next engineering work is actual control-flow disassembly / targeted decompilation of the extracted binaries, not additional socket probes or arbitrary PIN tests.
