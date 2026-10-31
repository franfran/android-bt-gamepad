# M3 DS3 — Specific integration implications of BlueZ 5.83 Sixaxis patch

**Scope:** offline analysis, no M3 modifications. See https://www.spinics.net/lists/linux-bluetooth/msg119483.html (April 24, 2025 v4 5/6) and BlueZ release 5.83 changelog.

## Confirmed BlueZ mechanism

The specific published patch is **not** a trivial per-MAC pre-auth bypass. It changes **both**:
1. Incoming HID listening servers for PSM 0x11 / 0x13 to `BT_IO_SEC_LOW` when an enrolled `CablePairing` device exists on the adapter (server.c/manager.c).
2. After an incoming HID connection is accepted, it checks `device_is_cable_pairing()`. For ordinary non-cable devices under `classic_bonded_only=true`, it rejects unbonded devices and raises security back to `BT_IO_SEC_MEDIUM`; for cable-paired devices it skips the bonding/encryption requirement (device.c).

**Subtle security consequence:** The initial lower-security listen setting is potentially adapter-wide for the HID servers, with selective enforcement performed later. It is inaccurate to describe this as a solely pre-auth, per-MAC kernel exception. Its safety depends on precisely staged HID admission and report filtering, with residual address-spoof risk. Do not duplicate the lowering mechanically in Android.

## What this changes for M3

- **M3 Gate A**: owner-original S8 native security level for HID registration was observed as mask `0x36` and the security callgraph can issue HCI Authentication Requested 0x0411 before incoming HID is established. A later Java callback cannot stop this earlier path. A supported M3 per-device policy setter *before* the security check would be ideal; no such API has been demonstrated.
- **M3 Gate B**: actual original M3 `HidHostService.okToConnect` demands `BOND_BONDED` and acceptable connection policy. BlueZ's unbonded path also needs a corresponding admission model at this later Android stage.
- Lowering the registered HID service security requirement indiscriminately would expose other devices **before** the Java check, regardless of later rejection; an exact address/PSM/provenance gate and early mitigation are required. Never set a global BTM mask or relax security for keyboards.
- M3's Android Fluoride HAL takes ownership of the Bluetooth controller; BlueZ's kernel socket `BT_IO_SEC_LOW` model is **not directly portable**.

## Exact remaining interface question

Can M3 expose a **supported** native policy decision before HCI auth with both (a) the incoming peer BD_ADDR (from the ACL/device record) and (b) the HID PSM 0x11/0x13 / service identity, while preserving ordinary security for other devices? Prior PRs already established that `btm_sec_l2cap_access_req_by_requirement` lacks PSM, so the decision must occur at a caller with retained PSM or require explicit, bounded context propagation. A static callsite alone does not prove it is safely callable from another Android process.

## Decision

**Architecture GO (offline only):** design a two-stage cable-authorized HID policy referencing this exact BlueZ patch, model spoofing and keyboard-report filtering, audit M3 callsite context, and verify the exact Java HID Host acceptance path.

**Live NO_GO:** broad HID security downgrade, post-auth-only Java receiver, fabricated bonded status/key, custom concurrent Bluetooth daemon, native injection and service restart. Maintain the Owner-approved one-time USB registration + later wireless-only objective.
