# I2/I6 — BTIF/JNI minimum-change surface and session propagation boundary

Pinned public H618 Android 12 Fluoride: `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. Source-only analysis. Not a promise of exact M3 OEM ABI compatibility.

## Confirmed profile ownership and callback path
1. [bluetooth.cc:416–442](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/bluetooth.cc#L416-L442) resolves `BT_PROFILE_HIDHOST_ID` to `btif_hh_get_interface()` from a fixed profile-interface dispatcher. **No third-party registration slot found here.**
2. [btif_hh.cc:1675–1690](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1675-L1690) provides static `bthh_interface_t`; [1714–1724](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1714-L1724) returns it. [1701–1708](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1701-L1708) enables the built-in BTA HID Host via `BTA_HhEnable(bte_hh_evt)`.
3. [Bluetooth JNI hid_host.cpp:226–233](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L226-L233) retrieves the static interface by profile ID and supplies `sBluetoothHidCallbacks`.
4. [JNI:54–70](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L54-L70) invokes Java `onConnectStateChanged(byte[] address,int state)`; method ID declared [JNI:193–196](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L193-L196). [Java:185–207](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L185-L207) checks `okToConnect` and may virtual-unplug; [Java:891–919](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L891-L919) rejects unbonded peers.

## Actual minimum impact is broader than one file
A hypothetical trusted cable-enrolled session signal cannot be manufactured in Java from `byte[] address, int state`. A real source-level proof may require **all** of:
- L2CAP/BTM integration around incoming HID control/interrupt access, with session and enrollment provenance.
- BTA/BTIF HID event linkage to the *same* native session and authorization generation (no normal bond forgery).
- A protected, explicit Native→JNI→Java interface or alternative supported privileged authorization service with secure source and revocation semantics.
- Java HidHostService consuming that grant while still enforcing quiet mode/forbidden policy and preserving unrelated devices.
- Revocation on disconnect, BTA cleanup, Bluetooth restart and adapter replacement, with no stale CCB or Java state access.
- Later UHID SET_REPORT request/reply repair investigated separately in PR #51.

Modifying the public `bthh_callbacks_t` ABI by adding fields is **not** a minimum-risk change: compiled JNI ↔ native struct-size and OEM binary mismatches are unverified. Prefer investigating a separate internal interface/state query rather than silently extending the existing callbacks; this is a **design hypothesis**, not a verified supported API. JNI and Java still require matching source changes and clean build/deployment.

## Research decision
- **Proven:** static built-in HID Host interface and address/state-only callback chain; Java's BOND_BONDED gate; native L2CAP PSM + CCB security callsite.
- **Unknown:** protected session transport architecture; secure peer attribution without cryptographic pairing; OEM build completeness and ABI; authorized cross-process lifecycle.
- **NO_GO:** treating `BT_PROFILE_HIDHOST_ID` as a plugin API, Java MAC whitelist, fabricated BOND_BONDED, global security downgrade, runtime process injection, or delivering a single native .so as a proven complete fix.

## Owner end-to-end acceptance
Wired DS3 already works in RetroArch. Owner permits a **one-time USB setup**, then expects cable-free DS3 wireless connect/reconnect and RetroArch gameplay without repeating USB enrollment. Wireless acceptance requires Native, Java and UHID gates; no regression in wired operation.

Next host-only task: produce a bounded state/epoch contract for a private authorization-query interface (data classification, owner, startup/shutdown lifecycle and adversarial cases), then check build feasibility separately in PR #51 without assuming the absent local BSP is present.

No live M3 operations or implementation authorized.
