# M3 DS3 — Deployment mechanism decision: Android 12 legacy stack, package boundary, and recovery

**2026-10-31, offline design.** Owner's aim remains one USB enrollment then built-in Bluetooth DS3 wireless input. No install, flash, injection or Bluetooth restart approved.

## New important platform-version distinction

AOSP documents the **modular Bluetooth APEX** as introduced in **Android 13**; the modern `com.android.btservices` APEX packaging examples apply to newer versions and cannot be assumed on this Android 12 M3. The owner-original M3 has a system-partition `Bluetooth.apk`, mapped `libbluetooth_jni.so` and `libbluetooth.so` evidenced by S7 and earlier package/ELF studies. **Do not design a btservices APEX swap or use modern APEX paths for M3.** Android generally layers Java Bluetooth profile app → JNI → native Bluetooth stack → vendor HAL; exact M3 paths still need owner-firmware-specific packaging confirmation.

Official references:
- https://source.android.com/docs/core/ota/modular-system/bluetooth — modular Bluetooth introduced Android 13.
- https://source.android.com/docs/core/connect/bluetooth — architectural layers.
- https://android.googlesource.com/platform/frameworks/base/+/android12-release/core/res/AndroidManifest.xml — `BLUETOOTH_PRIVILEGED` is `signature|privileged`, `BLUETOOTH_STACK` is `signature`; generic user APK/root shell context is not a granted Bluetooth stack interface.
- https://source.android.com/docs/security/features/verifiedboot/verified-boot — replacing verified system contents may break AVB/dm-verity, require offline backup and boot recovery; cannot infer actual target AVB state.
- https://source.android.com/docs/core/ota/dynamic_partitions/implement — dynamic partition / AVB interaction.

## Three deployable families to evaluate, NOT presently authorized

1. **Runtime plugin into existing Bluetooth process (S7)**: no system-APK signing requirement for the add-on itself, but must solve service linker namespace, safe entry/rollback under 49 threads, actual interception at native ingress, and **separate Java HID Host bond gate**. There is *no proof the loaded addon will be called*; C4C-3 remains NO_GO. More loader tests in owned processes cannot independently resolve the production linker-namespace/policy hook.
2. **System/firmware Bluetooth package modification**: would allow native security and Java HID Host changes in one controlled platform codebase, but native `libbluetooth.so` ABI compatibility, APK certificate and Android package verification, partition integrity, AVB/dm-verity, boot/recovery access are unresolved. Owner already evaluated 2025 firmware and chose not to flash it because no DS3 fix; do NOT confuse this with a user-authorized custom image.
3. **Privileged PIN/receiver helper**: Android 12 grants `BLUETOOTH_PRIVILEGED` only to `signature|privileged` callers. Even if permissions are obtained, helper doesn't control the **native** pre-auth security outcome or the Java `BOND_BONDED` gate for a nonbonded cable-paired DS3; remain a conditional diagnostic path only, *not preferred end-to-end solution*. Avoid racing OEM pairing receiver.

## Correct milestone sequence

- **Step 1 (NOW, offline)**: determine which exact original system APK / JNI / stack files are loaded on M3; record paths, signatures/privileged deployment properties if available from archived artifacts. Audit whether any OEM supported extension exists — do not claim absence from public API list alone.
- **Step 2 (offline)**: design scoped entry rule for Classic incoming PSM 0x11 and 0x13 only, with owner-authorized enrollment and explicit refusal of unrelated devices; show both native and Java admission behavior in a mocked integration test. Do not translate a candidate decision into a forged bonded/cryptographic state.
- **Step 3 (NO-GO for runtime)**: compare S7 service loader safety, namespace, recovery and Java integration against offline modified-stack option using **device-specific** AVB/signature state and independent recovery. Neither can be called low-risk by default.
- **Step 4 (requires separate Owner approval)**: any observed/service-side loader test, APK/stack replacement, restart, or wireless DS3 attempt. Current owner approval is for investigation/documentation only.

## Decision and correction

**No supported easy "Bluetooth plugin" API has been verified.** Crucially, the Android 13+ Bluetooth APEX/module update model is not a workaround for M3 Android 12. A stand-alone PIN helper should not remain the leading implementation plan while pursuing nonbonded Sixaxis cable pairing; the open Draft PR's filename/title are historical and should be understood as research-only. Primary next gate is **evidence of viable native/Java integration with rollback**, not another PIN guess or more tests of USB input (which is already PASS).

**Deployment status: BOTH runtime injection and system patch remain NO_GO.**
