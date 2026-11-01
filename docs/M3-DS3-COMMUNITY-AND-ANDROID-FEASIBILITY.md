# M3 DS3 Wireless — Consolidated Offline Feasibility Assessment

**Recorded:** 2026-10-31. **Scope:** complete decision-quality review of public community implementations and archived RetroBox S8 evidence accessible in this repository. **No device access / changes.** This is a consolidated report, not repeated reverse engineering.

## Decision

**NO_GO for a PIN-only helper, empty PIN experiment, and a generic nonbonded HID toggle. GO for a strictly offline M3-specific two-gate verifier based on the owner-original Bluetooth APK when supplied locally.**

There is **no demonstrated patch-free solution** for this specific vendor Android 12 Bluetooth stack. BlueZ is a useful design source, not a drop-in integration. A USB-enrolled device's host BD_ADDR registration is not equivalent to a secure Bluetooth bond. Existing S8 evidence shows an incoming HID PSM connection triggering M3 native HCI Authentication Requested, while unrelated app UI shows a conditional null-PIN problem.

## Three different concepts that must not be conflated

1. **Cable registration**: BlueZ `sixaxis.c` obtains controller address via USB and sets the controller's central/master host Bluetooth address (Feature 0xF5). BlueZ additionally registers a HID SDP record and marks its own device as cable-paired/trusted through internal daemon APIs. This is **host-side authorization plus controller configuration**, not Bluetooth HCI link-key/PIN bonding.
2. **macOS `ds3activate` empty PIN**: `devicePairingPINCodeRequest` invokes `replyPINCode:0 PINCode:&pin`. This means a zero-length **macOS API delegate response**. It does not prove an HCI zero-length positive reply can succeed or Android accepts an empty byte array. In particular `BluetoothDevice.setPin(null)` is not a zero-length PIN.
3. **Classic Bluetooth authentication**: M3 archived S8 actual native code constructs HCI Authentication Requested (opcode 0x0411) during incoming L2CAP HID processing; old HCI evidence subsequently shows missing replies / status 0x22. Bypassing an OEM Java PIN UI alone does not undo the native security requirement.

## Source evidence hierarchy

| Claim | Evidence | Confidence |
| --- | --- | --- |
| DS3 USB host enrollment is established | BlueZ `plugins/sixaxis.c` USB + `btd_request_authorization_cable_configured` + HID SDP/device cable-pairing routines | Direct upstream source |
| BlueZ considers unbonded DS3 a real security compatibility problem | BlueZ issue #1165, April 2025: BT_IO_SEC_MEDIUM triggers encryption/PIN not expected; discusses per-MAC admission, HID report filtering and remaining spoofing risk; issue is **design discussion** | Direct maintainer discussion; **not proof a fix shipped** |
| BlueZ has a global `ClassicBondedOnly` workaround | BlueZ input.conf and ArchWiki | Confirmed; **prohibited for M3** due to broader unauthorized HID/CVE risks |
| macOS utility uses zero-length delegate response | `crux161/ds3activate` `ds3activate.c` | Direct source, macOS-specific |
| Android HID host has a bonded-state admission check | AOSP `HidHostService.okToConnect` in multiple historical/current branches | Direct AOSP source **only**, actual vendor M3 branch not checked from bytes in this run |
| M3 native path issues HCI authentication | RetroBox S8 PR #25, #28, #33, #39, #40 originally SHA-pinned M3 `libbluetooth.so`, SHA256 `4ce119ed...4962bd85` | Previously verified original M3 static ELF + historical HCI; runtime branching unproved |
| M3 Java PIN callback and vendor null PIN behavior | PR #48 and PR #49: owner-original exact `TvSettings.apk`, `Bluetooth.apk` and framework DEX | Verified static conditional path; runtime min16Digits unknown |
| Exact M3 `HidHostService.okToConnect` and per-device override availability | M3 proprietary APK not present in this workspace; upstream equivalent is not the device | **UNVERIFIED** — cannot claim measured M3 behavior |
| M3 supports a safe public per-device nonbonded HID admission API | No evidence in M3 documentation or standard Android API researched here | **UNVERIFIED; do not assume** |

## Why the proposed simple fixes cannot be approved

**A. Zero-length PIN:** The macOS API's length=0 is not equivalent to Java null; Android `setPin(byte[])` could be callable via `BLUETOOTH_CONNECT` on API 31 but compatibility, length validation and native PIN behavior depend on the actual service. No proven evidence that a zero-length PIN achieves bond, authenticates LMP, or passes HID host bonded check on M3. **NO_GO**.

**B. Privileged pairing receiver:** The only demonstrated OEM failure is conditional PIN variant 0 → `setPin(null)`. Answering with a made-up code is wrong; even if it replies successfully, native link authentication and Java HID Host admission may still fail. Broadcast ordering, exclusive ownership and OEM handler competition remain unknown; privilege is not a routing guarantee. **NO_GO as sole solution**.

**C. Generic nonbonded profile allow/Trust flag:** BlueZ's `btd_device_set_trusted`, SDP registration, and cable authorization are inside Linux bluetoothd and do not map to a documented Android Java trust API. `setConnectionPolicy(ALLOWED)` is a profile preference, **not** proof of bypassing bond security. Changing bond database, faking `BOND_BONDED`, or broad auth downgrade is prohibited. **NO_GO**.

**D. M3-specific native exception:** This is where the demonstrated S8 0x0411 route originates. A future patch could theoretically constrain HID PSM 0x11/0x13 *and exact USB-enrolled address*, plus separate HID host admission, but spoofing remains, protocol metadata could be missing at a proposed hook point, and actual invocation safety is unresolved. Previous C4C-3 injection **NO_GO** remains. **DESIGN-ONLY**, not execution.

## Actual M3 two-gate map from available facts

```text
DS3 USB-enrolled to M3 host address                         [verified previous owner work]
  -> DS3 initiates HID PSM 0x11 L2CAP                        [historical capture]
    -> M3 native L2CAP/BTM security callsite                 [S8 static path]
      -> HCI opcode 0x0411 Authentication Requested          [static + historic HCI]
        -> PIN request / Java broadcast                       [historic logs]
          -> OEM TvSettings null argument for variant 0       [static conditional]
          -> unknown actual min16Digits / variant             [runtime MISSING]
        -> auth complete 0x22                                 [historic HCI]
    -> HID profile admission / okToConnect                    [AOSP bonded gate; M3 MISSING]
      -> Android InputManager -> RetroArch                    [wireless NOT REACHED]
```

Important nuance: static HCI 0x0411 route is established but the exact live branch predicates are not; the actual M3 `okToConnect` body remains unexamined, and on devices callbacks may be placed differently. Do not conflate source/reference with M3 measured.

## One definitive remaining offline action

**Inspect only actual 2024 M3 Bluetooth APK (SHA-256 `d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f`)**. Existing PR #49 verifies its PIN variant logic but **does not** document its HID Host admission logic.

Minimum verification worksheet (offline, no APK published):
1. Validate SHA-256 and package identity; enumerate all matching `Lcom/android/bluetooth/hid/HidHostService;`/related classes across `classes*.dex`, or document absent/vendor relocated.
2. Decode actual `okToConnect(BluetoothDevice)`, `connect`, incoming state callback, `getBondState`, `getConnectionPolicy`, `BOND_BONDED` operands and branch directions. Record offsets and direct, inferred, absent outcomes; don't substitute AOSP disassembly.
3. Search actual service `BluetoothDevice.setPin(byte[])` binder path and bounds (or confirm upstream only); verify whether `setPin(new byte[0])` is rejected **without executing**.
4. Enumerate manifest pairing broadcast intent filters, exported/priority and receiver ownership from exact OEM `TvSettings.apk`/Bluetooth APK; actual order needs runtime proof if relied upon.
5. Cross-reference S8 already SHA-pinned BTM/L2CAP callsites rather than recreate them. Determine if any supported *pre-authentication per-device policy hook* is actually exported. Record NO_GO if not.
6. No sensitive device addresses or proprietary APKs committed. An independently owned offline test fixture is permitted.

Because the actual APK bytes are not in this session, items 1–5 **cannot honestly be labeled completed**. This is an explicit prerequisite to concluding whether there is a patch-free path.

## Engineering choice after that read

- If M3 contains a documented per-controller cable-authorization and nonbonded HID extension that controls **both** gates, prepare a static standalone proof and a separately approved one-shot on-device diagnostic. No installation yet.
- If M3 has a hard `BOND_BONDED` check and its native security requirement is fixed, **a standalone Java helper without modifying those gates is NO_GO**. Favor an offline, narrowly scoped source patch feasibility study on exactly matched vendor artifacts. Prefer a reviewable boot-safe solution over unsafe live process injection; don't promise writable system partition or verified signature support.
- If actual M3 gates are permissive but only PIN path blocks, re-evaluate PIN behavior with source-proven DS3-specific response; keep zero-length hypothesis unverified and require a minimum runtime variant measurement before tests.
- Any privileged APK install, system service restart/replacement, permissions tweak, native patch, firmware flash, or pairing attempt requires fresh explicit Owner approval and recovery plan.

## Safety and rollback contract

Trusted DS3 identification requires physical USB enrollment plus persisted controller identity, revocation, expiration, and an explicit owner-controlled one-shot. A MAC whitelist is **not cryptographic authentication** and could be spoofed; prohibit keyboard reports from that exceptional insecure path if future design allows it. Do not grant arbitrary HID access to unknown devices. Preserve normal Bluetooth security for all other devices. Use verified Wi-Fi ADB with USB fallback and independently demonstrated rollback before any deployment; there is no guaranteed rollback of native linker injection. No modified system APK, boot hook, live restart, global configuration or encrypted-link bypass currently authorized.

## Primary links

- https://kernel.googlesource.com/pub/scm/bluetooth/bluez.git/+/a93047cd044fb17d687f43bef95289ec834876b2/plugins/sixaxis.c
- https://github.com/bluez/bluez/issues/1165
- https://github.com/bluez/bluez/blob/master/profiles/input/input.conf
- https://github.com/crux161/ds3activate/blob/main/ds3activate.c
- https://android.googlesource.com/platform/packages/apps/Bluetooth/+/refs/heads/master/src/com/android/bluetooth/hid/HidHostService.java
- https://developer.android.com/reference/android/bluetooth/BluetoothDevice
- RetroBox PR #48, #49, #25, #28, #33, #39, #40, Issue #6.
