# RetroBox M3 DS3 — One-time USB enrollment, wireless-only operation

**Owner requirement (2026-10-31):** A one-time USB setup is acceptable; subsequent play must use the M3's *built-in* Bluetooth, without cable, dongle or external bridge. USB DS3 input and RetroArch navigation already PASS. USB `sixpair` host-address enrollment already performed. **Do not redo wired tests.**

## What BlueZ 5.83 does and does not provide
BlueZ's cable-pairing model associates an intentionally USB-enrolled Sixaxis device with a Bluetooth HID policy, so later PS-button initiated incoming Bluetooth can be admitted without ordinary encrypted link-key bonding. Upstream 5.83 addresses cable-paired Sixaxis specifically. This is a **reference design** only; M3 Android 12 uses Fluoride, not BlueZ.

An important distinction: writing the host BD_ADDR with USB report 0xF5 does **not itself create an Android BOND_BONDED record**, doesn't install a valid link key and doesn't grant access through the Android HID Host. The macOS zero-length PIN delegate example similarly does not prove an Android shortcut.

## M3 measured gates
1. **Native authentication:** existing S8 owner-original libbluetooth.so callgraph finds incoming HID/L2CAP security can lead to HCI Authentication Requested 0x0411, historically preceding HCI 0x22 failure. Exact runtime branch remains unverified.
2. **HID Host:** exact SHA-matched owner 2024 Bluetooth.apk `HidHostService.okToConnect(BluetoothDevice)` at DEX code offset 0x26e880 requires `getBondState(device)==12` (BOND_BONDED), then connection policy -1 or 100. This is M3 firmware code, **not simply an AOSP analogy**. Existing Android cannot pass a nonbonded DS3 through this check unchanged.

## Candidate solutions, decision
- **Existing supported vendor cable-pairing extension:** BEST if demonstrated; no evidence found to date. Do not infer from BlueZ or root privileges. Locate a callable interface *before* both native and HID gates, or mark absent/unverified.
- **Genuine normal Bluetooth bond:** Would satisfy HID admission without patching it, but established community Sixaxis cable-pairing suggests DS3 may not complete normal encrypted bond. No proven Android-compatible non-guess PIN response. **NO_GO for a blind PIN/empty PIN trial**.
- **Scoped cable authorization integration:** Most plausible future design if no supported vendor extension. A reviewed policy would need explicit USB enrollment, precise controller identity, HID-only PSM 0x11/0x13, native per-connection admission and Java HID admission; all other devices use existing security. MAC equality alone is spoofable and insufficient as strong authentication. Restrict HID report types where possible, plan revocation, and acknowledge residual spoofing risk.
- **Live injection / blanket security change / faked bond:** **NO_GO** under current Owner constraints.
- **OEM APK replacement / verified system patch:** *Design fallback only*, may require platform keys, privileged placement, verified boot handling and recovery. No installation or service restart authorized.

## Offline implementation contract (not production code)
```
enrollment = { controller_identity_from_physical_usb,
               enrolled_host_BD_ADDR,
               owner_approved, revoked, enrolled_at }
request = { remote_controller_identity, host_adapter_address,
            l2cap_psm, native_security_stage, hid_profile_stage }

ALLOW_CABLE_CANDIDATE only if:
  owner_approved AND NOT revoked
  AND verified physical USB enrollment on this exact M3 host
  AND controller identity matches
  AND adapter address unchanged
  AND PSM IN {0x11,0x13}
  AND request is specifically for HID Host
  AND both native gate and HID gate provide a verified scoped hook
  AND policy is not enabled for other HID/keyboard devices
otherwise DENY
```
This is an **authorization policy hypothesis**, not a cryptographic identity verification mechanism, Android executable, or authority to alter a live device. Recording a MAC does not defeat spoofing. Never create LinkKeys or `BOND_BONDED` artificially.

## M1 GO/NO_GO
**GO now:** offline source-only evidence matrix and small mock-policy tests for reject/expiry/revocation/wrong adapter/wrong PSM/unrecognized device/duplicate attempts. Use exact-original M3 APK and prior S8 callgraph; no further broad reverse engineering.

**NO_GO for device deployment** until (a) specific native **pre-auth per-device** extension and specific Java HID admission integration or safely reviewable changes are identified, (b) independent Wi-Fi ADB + USB fallback and rollback are validated, (c) no global downgrade, (d) scoped Owner approval for each live modification.

**Success acceptance (later, separately authorized):** unplug DS3 after one-time enrollment, press PS, verify BT link and scoped admission, obtain wireless Android InputDevice, then navigate RetroArch menus wirelessly, repeat reconnect after disconnection and M3 reboot. No more wired functional retesting.

## Supporting evidence
- PR #49 (OEM null PIN/firwmare comparison); original APK SHA256 `d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f`.
- RetroBox S8 PRs #25, #28, #33, #39, #40; Issue #6.
- BlueZ 5.83 Sixaxis cable pairing and BlueZ #1165: https://github.com/bluez/bluez/issues/1165 .
