# RetroBox Stage 3C — Gate 1: M3 Bluetooth APK DEX Evidence

## Scope and status

Offline analysis of the user-extracted M3 Android 12 `/system/app/Bluetooth/Bluetooth.apk` (`com.android.bluetooth`). **Concrete APK-level code evidence obtained; native authentication patch is NOT located or ready to deploy.** No M3 device files were modified.

## Inputs

- APK: `bluetooth-1.apk` from `m3-bluetooth-analysis.zip`, 8,458,801 bytes.
- Contains one `classes.dex` (7,543,572 bytes), DEX version 039.
- Native libraries separately provided: ARM32 `libbluetooth.so` and `libbluetooth_jni.so`.

## DEX code locations (file offsets inside classes.dex)

By reading the DEX header, strings/type/method/class tables, class_data encoded methods, and code_item offsets (not merely grepping symbols):

| Class | Method | DEX code_item offset | Meaning |
|---|---|---:|---|
| `com.android.bluetooth.hid.HidHostService` | `okToConnect()` | `0x26e880` | **Actual M3 connection-authorization function** |
| same | `connect()` | `0x26e6c4` | Profile connection request path |
| same | `onConnectStateChanged()` | `0x26f254` | Profile connection-state callback |
| same | `getConnectionPolicy()` | `0x26eca4` | Connection policy lookup |
| `com.android.bluetooth.btservice.BondStateMachine` | `createBond()` (private method) | `0x239d74` | Java bonding state-machine flow |
| same | `getUnbondReasonFromHALCode()` | `0x239fb8` | Translates native bonding failure reason |

The `HidHostService.okToConnect()` code_item has **94 DEX code units**. The following are *actual `const-string` instructions* inside the method; their full DEX file offsets are:

- `0x26e8c2` → `okToConnect: return false as quiet mode enabled`
- `0x26e8f0` → `okToConnect: return false, bondState=`
- `0x26e928` → `okToConnect: return false, connectionPolicy=`

These exact code-level string references confirm that the **extracted M3 binary has an incoming HID-host authorization branch that checks bond state**, consistent with the AOSP implementation. This is stronger evidence than matching strings elsewhere in the APK. **It does not establish that this branch caused the observed failure**, because the measured Bluetooth HCI session timed out at authentication (`0x22`) before successful HID connection.

Important: All offsets above are **inside `classes.dex`**, not `Bluetooth.apk` ZIP container offsets, not native ELF virtual addresses, and **not patch recommendations**. The `BondStateMachine.createBond` listed above is an encoded private method, and the APK may contain other overloads/inherited service methods.

## Native authentication: still unresolved

Earlier ELF audit showed corresponding strings in `libbluetooth.so` including `btm_sec_pin_code_request`, `btm_sec_auth_complete` and `btm_sec_link_key_request`, and valid Thumb-2 instructions, but **did not produce a verified security function call graph or DS3-specific patch branch**. Static analysis of the Java HID gate is not enough to bypass the **30-second HCI authentication timeout**. No safe native patch or APK alteration has been produced.

## Architecture decision

The controller connection remains on Android's vendor-HAL → Fluoride path; Linux Bluetooth `socket()`/`bind()` tests do not demonstrate a usable HCI controller, since `/sys/class/bluetooth` had no `hci0`. The proposed path remains targeted handling of cable-paired DS3 inside Android's existing stack, but must be implemented and tested without globally weakening security.

## What a safe Stage 3C Gate 2 requires

1. Reverse engineer the precise native authentication decision path in **this** `libbluetooth.so`; ideally reproduce the logic as a source-level Android 12 Fluoride patch instead of hex-editing a stripped library.
2. Determine which events occur **before** the 0x22 timeout and distinguish controller-level LMP nonresponse from host policy rejection.
3. Patch only an explicitly allowlisted DS3 that has undergone owner-controlled USB cable pairing; do not fabricate LinkKeys or globally disable bonding.
4. Deploy first by a reversible systemless overlay or a replaceable test image with a verified rollback route; never blind overwrite `/system/lib/libbluetooth.so`.
5. Acceptance: wireless DS3 produces `GAMEPAD|JOYSTICK` Android input events, then RetroArch picks up the controller (mapping might require wireless profile).

## Reproducibility

DEX offsets were extracted by a small `struct`-based parser: parse `string_ids`, `type_ids`, `method_ids`, `class_defs`, LEB128 class_data entries, and each `code_item` (16-byte header); locate `const-string` opcode `0x1a` pointing to the three exact DEX string IDs within the 94-unit `okToConnect` bytecode. This does not require a decompiler or a network dependency.

## Outcome

**Gate 1 Java/APK path: verified. Gate 1 native authentication path: incomplete.** The evidence is sufficient to avoid speculative Java-only patches, but is *not* sufficient to ship or run a system Bluetooth modification.
