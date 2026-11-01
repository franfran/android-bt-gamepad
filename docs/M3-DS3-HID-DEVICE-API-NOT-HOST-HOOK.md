# Android 12 Bluetooth extension audit — HID Host vs HID Device

**2026-10-31, offline only.** This audit closes a misleading public API candidate. It does not claim a complete exhaustive audit of OEM proprietary native extensions.

## Critical API directionality

Android framework's public `BluetoothHidDevice.registerApp()` makes the *Android box act as a HID peripheral*, not the HID **Host** accepting an inbound Sony DS3. AOSP Android 12 explicitly warns that HID Host service is disabled while the app registers in HID Device mode. Therefore creating a DS3 "plugin" using this API is both the **wrong role** and likely **counterproductive**.

Evidence: https://android.googlesource.com/platform/frameworks/base/+/android12-release/core/java/android/bluetooth/BluetoothHidDevice.java and Android developers BluetoothHidDevice documentation.

## Original M3 native evidence

S8's `hidh_conn_reg` registers HID host Control/Interrupt L2CAP PSMs under global security mask `0x36`, whose incoming Classic L2CAP security callsite retains remote BD_ADDR and PSM. The Android API for HID Device SDP registration is not a per-peer native Host admission callback, cannot replace those registrations, and does not change exact M3 `HidHostService.okToConnect` BOND_BONDED requirement.

## Known mechanism options

1. **Documented BluetoothHidDevice app callback:** **NO_GO** — wrong role; Host service disabled while in use.
2. **Normal Android companion app / root service:** no proved access to native Host security decision or Java Host bond gate.
3. **S7 inert native plugin loaded via dlopen:** mapping library is not a policy hook. Tests passed only in independent M3 owned process; live Bluetooth loader remains C4C-3 NO_GO.
4. **Supported OEM native HID Host admission callback:** no demonstrated registration/export; requires direct binary interface evidence before accepting.
5. **Scoped modified Bluetooth Host stack:** possible design candidate, but need source/ELF patch surface, system privilege/signature, AVB/integrity and rollback evaluation. No installation/restart authorized.

## Discriminating next step

Avoid designing the wrong app/API. Determine whether a **supported, callable HID Host ingress callback** exists on this exact M3 build, or whether only internal stack code can make the security decision. Then compare **live plugin interception versus static stack modifications** against deployment and independent recovery constraints, without assuming any path is safe.

Keep BlueZ 5.83 as design reference only; it uses different controller/stack architecture. One-time USB sixpair enrollment is completed; USB HID / RetroArch already PASS.
