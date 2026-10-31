# M3 actual package signing/UID evidence — offline reconciliation

Date: 2026-10-31. Sources: archived owner `m3-bluetooth-package.txt` and `m3-tv-settings-package.txt` from `dumpsys package`. No on-device operations.

## Confirmed from archived M3 package dumps

| Property | Bluetooth service | TV Settings |
|---|---|---|
| Package | `com.android.bluetooth` | `com.android.tv.settings` |
| Code path | `/system/app/Bluetooth` | `/system/system_ext/priv-app/TvSettings` |
| UID | 1002 | 1000 |
| sharedUser | `android.uid.bluetooth/1002` | `android.uid.system/1000` |
| Native ABI | `armeabi-v7a` | not established here |
| `BLUETOOTH_PRIVILEGED` | `granted=true` | `granted=true` |
| Package signature dump | `PackageSignatures{... version:3, signatures:[5f5a234d] ...}` | `PackageSignatures{... version:3, signatures:[5f5a234d] ...}` |

The repeated `5f5a234d` is a **short Android dumpsys Signature rendering, not an independently obtained X.509 SHA-256 fingerprint**. It suggests the same Android representation was emitted for the two packages in the respective captures, but **does not establish certificate content, signing private-key availability, or the ability to resign modified packages**. Check actual APK signer certificates offline from owner originals before asserting certificate equivalence. Even confirmed certificate equality would not supply the private key.

## Engineering impact

- Both stock packages already have privileged Bluetooth permission. A **new** companion app does **not** inherit privileges just because an existing package has them.
- `com.android.bluetooth` runs in `android.uid.bluetooth`, while TV Settings runs in `android.uid.system`. They are different Linux security identities, and an app deployed under the wrong UID is not a transparent replacement.
- A modified in-place APK needs compatible certificate/PackageManager install and sharedUser handling; it also faces system image, AVB, SELinux and recovery constraints. `system/app` vs `system_ext/priv-app` is a real partition boundary.
- Runtime S7 plugin avoids replacing the on-disk APK but cannot automatically patch Java's `BOND_BONDED` or guarantee safe linker injection/hooking.
- A pure Java PIN receiver fix would not suffice for the BlueZ-style nonbonded HID route, and MAC-only trust is not cryptographically strong.

## Native firmware comparison status

The owner-supplied 2025 International extraction previously verified `TvSettings.apk` and `Bluetooth.apk` byte-identical to 2024 originals, while relevant `framework.jar` BluetoothDevice PIN methods were unchanged. **A SHA or build-ID comparison of the 2025 native `libbluetooth.so` against the 2024 original has NOT been completed** in this review. The retained owner upload presently available is the old `Bluetooth.apk`; do not claim the newer native implementation is identical or request a flash. Extracting a native library from the downloaded 2025 image remains a separate optional offline task if the actual image bytes are available.

## Security and current gate

These are archive-derived facts, **not** authorization to install modified APKs, impersonate system UID, replace files on verified partitions, bypass authentication, or inject into the live Bluetooth process. S7-C4C-3 NO_GO remains, and PR #50 is draft.

References: `docs/S7-C4C-HANDOVER.md`, `docs/SAFETY.md`, `docs/M3-DS3-OEM-PACKAGE-ROLLBACK-GATE.md`, PR #49.
