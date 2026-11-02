# I2/I6 — Cable-enrollment trust handoff: native ↔ Java

**Status:** design-only, no authorization to patch or run on M3. Based on previous PR #50 BlueZ 5.83 cable-pairing research, the source-first pinned H618 tree, and Owner-approved USB-first wireless-only workflow.

## Baseline and scoped trust distinction
- **Verified:** DS3 wired USB input works with M3/RetroArch. Owner permits USB **once** for setup; afterward PS button must allow Bluetooth wireless gameplay, reconnect and reboot without re-enrollment.
- USB feature report F5 sets the DS3's target Bluetooth host address. This is **device configuration**, not a signed authentication statement or conventional Bluetooth link key.
- A protected enrollment database can persist a policy decision across reboots, but **name, Class of Device, VID/PID, and BD_ADDR do not constitute cryptographic proof that a live radio peer is the same physical controller**. Without an additional viable proof of possession, a per-address admission gate carries spoofing risk. Do **not** claim strong trust based on USB history alone.

## Pinned Java gate
[HidHostService.java lines 185–207](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L185-L207) receives HAL CONNECTED and calls `okToConnect` before broadcasting. On failed admission, invokes `virtualUnPlugNative` (only newly connected transition).

[HidHostService.java lines 891–919](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L891-L919) requires adapter service present, enforces quiet mode and policy, and rejects `bondState != BOND_BONDED`. This is corroborated by PR #50 OEM APK bytecode. Therefore: a native-only CablePairing exception still fails Java Gate B, and a Java-only grant cannot prevent the earlier HCI authentication.

**Do not** simply change the comparison to `bonded || MAC in allowlist`: MAC address alone is spoofable and Java `BluetoothDevice` does not convey a verified native session epoch.

## Proposed protected, ephemeral grant (conceptual, not implemented)
Separate two state domains:
1. **Persisted USB enrollment**: one selected controller, adapter identity/version, enrolled master address, owner-approved lifecycle, generation, revocation marker. Use private, protected on-device storage (exact storage provider, permissions and integrity unverified). No `BOND_BONDED` fabrication.
2. **Native live admission capability**: new unpredictable session ID or unguessable token tied to a *verified* enrolled controller, BR/EDR ACL connection generation, peer, direction, HID PSM 0x11/0x13, channel generation, deadline and revocation generation. Need to prove whether true live peer identity is supportable; address is *only* a routing index.
3. **Java consumption**: protected native→Java transport forwards a short-lived, single-session, revocable admission **after** Native Gate A authorizes and before Java handles connected-state. It must be immune to public app broadcasts and replay; Java must check the native session rather than public address alone. Current upstream callbacks only convey `RawAddress*` and state, not a session capability; thus **an explicit source-integrated bridge or contract extension is required**. Do not assume it already exists.

## Recommended fail-closed transition model
`UNENROLLED → USB_ENROLLED → ACL_OBSERVED → CONTROL_AUTHORIZED → INTERRUPT_AUTHORIZED → JAVA_ADMITTED → UHID_READY → WIRELESS_ACTIVE`.

- Every state transition is conditional on authenticated provenance and the exact current epoch. If provenance cannot be shown, do not transition.
- On disconnect, expiry, unexpected parallel channel, adapter identity change, owner revocation or invalid Java policy, clear ephemeral grants and revert to a non-active state.
- Reconnect after ACL disconnect must create a **new** ephemeral session/grant while reusing only the still-valid USB enrollment.
- On reboot, ephemeral grants must never survive. Only the minimal persistent enrollment record can be re-evaluated after Bluetooth is ready. Ordinary devices use unmodified security rules.
- Unknown/unauthorized HID reports must not become a keyboard/mouse injection surface. An allowlist by device class or name is inadequate.

## Source-verified constraints
- Native completion in [l2c_link.cc:266–325](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_link.cc#L266-L325) matches an existing CCB pointer, but not an epoch token; stale/pointer-reuse lifecycle requires further proof.
- HAL HID `connection_state_cb` presently passes address+state ([BTIF hh](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L772-L831)) through [JNI](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L54-L70) to Java; a secure session ID is not passed there today.
- Thus a protected native-to-Java authorization proof must be separately designed and evaluated. Without it, Java acceptance by address alone is **NO_GO**, even if native access succeeds.

## Offline negative-test specification
| Case | Expected |
| --- | --- |
| No USB enrollment / old host master / revoked record | Reject CablePairing |
| Same MAC but unverified radio peer | Reject high-trust admission; document spoofing gap |
| Unrelated HID keyboard / non-DS3 / unknown PSM | Existing default security only |
| Interrupt PSM before authorized control in same ACL epoch | Reject/defer according to proven protocol ordering |
| Java handler receives CONNECTION_STATE_CONNECTED without matching live native grant | Virtual-unplug / reject per existing policy |
| Native grant from older epoch / stale callback / CCB pointer reuse | Reject and revoke |
| Quiet mode enabled / explicitly forbidden policy | Preserve existing rejection |
| Normal ACL disconnect/reconnect | Re-evaluate persistent enrollment and create new ephemeral grant |
| M3 reboot | No live grant persists; revalidate enrollment if safely possible |
| Missing UHID SET_REPORT actual completion | Not WIRELESS_ACTIVE; never forge reply |

## Engineering GO/NO_GO and next proof
**Research GO only.** Need evidence for: (1) safe radio peer attribution against MAC spoof, or a bounded risk policy approved by Owner; (2) protected session/epoch propagation through BTIF/JNI to Java; (3) buildable source matching OEM interfaces; (4) faithful HID input restrictions and report completion. Until then **do not implement a Java MAC allowlist or global native security exception**.

No M3 pairing attempt, USB enrollment rerun, Bluetooth restart, APK replacement, injection, runtime write or repository merge authorized.
