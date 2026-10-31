# M3 DS3 — Actual firmware package boundaries and rollback gate

**2026-10-31, offline-only.** This document corrects generic Android 12 deployment speculation with owner-M3 evidence in PR #49. No package modification, loader, service restart, flashing or pairing test authorized.

## Device-specific package facts (from owner's original M3)

- Original M3 `Bluetooth.apk` is at **`/system/app/Bluetooth/Bluetooth.apk`**, package `com.android.bluetooth`. Original 2024 and extracted 2025 International APK are SHA-identical (`d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f`).
- OEM `TvSettings.apk` is at **`/system/system_ext/priv-app/TvSettings/TvSettings.apk`**, package `com.android.tv.settings`. The old/new International firmware pair is SHA-identical (`70d8fdd66f6b0bd3a06f30e4d755b709f2026955fda3955bff537840b15d2225`). The OEM receiver passes null to `setPin(String)` for PIN variant 0.
- `framework.jar` is **`/system/framework/framework.jar`**, with unaffected `BluetoothDevice.setPin(String)` entry; 2025 differs in another DEX only.
- Bluetooth process uses `libbluetooth_jni.so` and owner-original ARM32 `libbluetooth.so` SHA `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`; mapped paths and package-signature capabilities should be sourced from original captured process/package artifacts, **not guessed**.
- `ro.build.ab_update=true`; device firmware lists `system/vendor/product/boot/vbmeta` partition families. The user extracted the 2025 International `super` into `system_a`, `vendor_a`, etc. These facts alone **do not prove** that both boot slots are populated, bootable, correctly verified or safely switchable.

## Significant deployment decision

1. The two Java components belong to **different APKs and partitions**: Bluetooth Host admission in system Bluetooth APK versus OEM legacy PIN UI in system_ext TV Settings. A simple TvSettings receiver fix is not an end-to-end BlueZ-style nonbonded HID solution.
2. Any on-disk solution must account for **at least native Bluetooth security + Java Bluetooth Host admission**, and preserve system integrity and signing. Whether TvSettings also needs adjustment depends on chosen pairing model; it is **not necessarily a third mandatory patch** for cable-paired nonbonded HID.
3. S7 in-memory native plugin may avoid updating native `libbluetooth.so` on disk, but **does not fix Java HID Host** or become callable just from `dlopen`. A complete plugin-based design needs a supported or separately validated Java-side integration strategy.
4. OEM APK version equality between 2024/2025 **does not establish native library equality**; do not claim newer firmware is useless for native behavior without extracting/comparing the right ELF. Owner has already decided against flashing; this comparison is optional offline evidence, not a reason to upgrade.

## A/B slot / AVB reality check

AOSP A/B describes an inactive slot as possible fallback, **but** that slot may be valid, outdated or unusable and slot metadata must be checked. A/B is not the same as assured recovery. AVB/dm-verity may reject modifications to verified partitions, and a failed firmware change may require physical board-level recovery. No live partition modification until independently validated.

References:
- AOSP A/B: https://source.android.com/docs/core/ota/ab
- AOSP AVB: https://android.googlesource.com/platform/external/avb/
- M3 owner-original evidence: https://github.com/franfran/android-bt-gamepad/pull/49
- Existing loader safety: docs/S7-C4C-HANDOVER.md, docs/SAFETY.md

## Specific remaining evidence / next offline work

- Inspect saved sanitized M3 package dump for exact Bluetooth package signing/privilege (normal `system/app` placement by itself is **not** evidence of a signature key or grant) and original recorded `/proc/PID/maps` native paths.
- If original 2025 extracted native ELF is available privately, compare **hash/build-id/security caller**, rather than repeating Java APK diff; do not require the owner to flash.
- Read-only target-only gate, if ever approved, should gather `ro.boot.slot_suffix`, `ro.boot.verifiedbootstate`, `ro.boot.vbmeta.device_state`, `ro.boot.veritymode`, `bootctl` slot metadata availability and independently verified USB ADB recovery; never equate property alone with actual rescue viability.
- For any proposed modified APK require signature compatibility, system partition placement, SELinux, app UID continuity and OTA/rollback. If platform signature cannot be preserved, record NO_GO for in-place APK overwrite; do not advise resigning with a self-generated key as if it were equivalent.
- Keep S7-C4C-3 target injection NO_GO and PR #50 draft.

## Owner acceptance unchanged

Existing USB sixpair enrollment + wired RetroArch input PASS. Final success requires detach cable, press PS, receive DS3 via built-in M3 BR/EDR, preserve all other devices' normal admission, and wireless RetroArch buttons/reconnect. No new USB test.
