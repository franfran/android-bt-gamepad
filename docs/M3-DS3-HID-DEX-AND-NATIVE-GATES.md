# M3 exact Bluetooth APK: confirmed admission boundary, remaining native hook

**2026-10-31 offline only.** Owner-uploaded original M3 Bluetooth APK locally inspected and SHA-verified against recorded firmware hash `d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f`. No device touched, no APK committed.

## Confirmed from M3 DEX, not upstream assumption

- Class `Lcom/android/bluetooth/hid/HidHostService;`, method `okToConnect(Landroid/bluetooth/BluetoothDevice;)Z`, DEX code offset `0x26e880`.
- `getConnectionPolicy(device)` at code-unit 31; `AdapterService.getBondState(device)` at 35.
- `const/16 0x0c` at 39; `if-eq v4,v5` at 41 branches to 64 **only when bonded**; otherwise logs `okToConnect: return false, bondState=` and returns false.
- `const/4 -1` at 64 and `if-eq` 65, or `const/16 100` at 67 and `if-eq` 69: allows only unknown/allowed policy. Otherwise logs reason and false; success return at 92.
- Original DEX has no literal `CablePairing` or `sixaxis` string. **A missing literal is not proof of absence of every vendor extension**.

This proves the *body* of the M3 `okToConnect` guard. It does **not** prove every possible incoming HID callback passes this method: caller reachability must be checked separately before claiming this guard necessarily blocks every incoming DS3. In particular, callback entrypoints may use a different state machine path. Keep source-vs-runtime distinction explicit.

## Existing M3 native S8 evidence

The archived S8 original-ELF studies identify registration of HID Control PSM 0x11 / Interrupt PSM 0x13 with security level mask 0x36, incoming L2CAP security calls, and a conditional path to HCI Authentication Requested 0x0411. This is powerful static evidence that **native auth is an earlier gate**, not an Android Java UI-only issue. However it doesn't demonstrate a public per-peer callback to replace a security requirement, nor establish why HCI 0x22 occurred.

## Most promising next offline investigation

Instead of redesigning Android PIN pairing again:

1. Verify the actual M3 `HidHostService` JNI event/state callback invokes `okToConnect` for incoming DS3 links, and confirm the exact return behavior; don't assume all incoming paths call it.
2. Examine whether the M3 native inbound HID PSM security registration **already has** a targeted per-peer authorization API or callback *before* auth (peer address, PSM, registered HID service). Prior S8 reports warn `btm_sec_l2cap_access_req_by_requirement` itself lacks PSM; favor its caller with sufficient context.
3. Audit the actual original Bluetooth APK for `CablePairing` support or a suitable exposed system API; missing obvious strings alone is weak negative evidence.
4. Compare BlueZ 5.83's **early low-security HID listen + late cable-device check** carefully: it is not magically per-MAC before auth and is not directly portable to M3 Fluoride. Any M3 approach must demonstrate it does not admit unknown HID/keyboard devices, including spoofed BD_ADDR.
5. Design any offline proof as a reversible, narrow source change *only after* caller and native hook feasibility. No runtime injection, system APK replacement, Bluetooth restart or test pairing without separate explicit owner approval.

## GO / NO_GO

**GO:** offline read-only caller mapping and native API surface feasibility. **NO_GO:** zero/guessed PIN, standalone PIN receiver as complete fix, fake bond/link key, global security downgrade, unreviewed binary patch, process injection. Existing C4C-3 NO_GO remains in effect.

Owner's objective remains one-time **already completed** USB enrollment, then DS3 PS button Bluetooth connection and full wireless RetroArch control; no wired-controller retesting.

## Additional direct caller evidence (same verified APK)

Inspected all DEX-declared methods of the `com.android.bluetooth.hid` classes for invoke references to method_id **24499** (`HidHostService.okToConnect(BluetoothDevice)`). One direct invoke candidate is found in `Lcom/android/bluetooth/hid/HidHostService$1;->handleMessage(Landroid/os/Message;)V`, DEX `code_off=0x26dc8c` at instruction/code-unit **452** (invoke-virtual method index 24499). At code-unit 455 the boolean result is read; at 456 an `if-nez` controls the branch. Nearby references are HID native disconnect and connection-state handling. This **substantially strengthens caller reachability** relative to simply finding an unused utility method.

**Still unverified:** exact incoming event identifier and complete control-flow ownership at that callback; no fresh M3 HCI run or log. A byte-level invoke reference proves the call exists in HID message handler, not that a particular DS3 event passed it. The corresponding event/callback predicate is the next narrowly scoped offline verification, without a general reverse-engineering restart.

**Engineering implication:** Unless actual DS3 callback takes an alternate path, incoming nonbonded connection will hit a hard Java bond check after the earlier native authentication gate. BlueZ-style cable authorization requires both an early native path and an accepted HID Host path; a PIN receiver alone has no demonstrated ability to satisfy them.

## Resolved incoming HID message dispatch (exact local owner APK)

Fresh read of the owner-uploaded SHA-matched `classes.dex` (no device access) resolves the `HidHostService$1.handleMessage(Message)` **packed-switch** at code-unit `0x000e`, payload `0x0250`. The payload has **16** entries for integer `Message.what = 1..16`. **Case 3** enters at code-unit `0x0195`; its control-flow body contains the already-observed `okToConnect()` invoke at `0x01c4` (method index `0x5fb3`, followed by result check). Thus the previously missing **message dispatch predecessor is proven**, not merely an orphaned call.

Trace contract: `Message.what==3` -> `handleMessage` case entry `0x0195` -> conditional code path `0x01c4` `okToConnect(peer)` -> true/false gating. Actual JNI event source which sends message code 3, and execution frequency for DS3 attempts, remain **UNVERIFIED**. This does not prove that a failed native security attempt ever reaches the Java handler. Do not infer live callback execution from this static case mapping.

### Why this changes implementation prioritization

A successful BlueZ-style cable-paired native connection would face an independently verified M3 Java bond gate on the case-3 path. **Both native security and Java state policy have to be accounted for**, but there is no requirement to patch Java before demonstrating safe native ingress. An APK-only helper answering zero/guessed PIN still cannot be considered a completed solution.

No runtime operations, firmware modifications, untrusted-controller enrollment or service restart.

## Case 3 branch-level proof: initial connection admission

Follow-up direct disassembly of exact SHA-matched M3 DEX, within `handleMessage` case 3 (`0x0195`):
- Code-unit `0x01b5` `if-nez v2` goes to `0x01b9` to obtain `Integer.intValue()` for previous HID state; absent map entry takes default path to `0x01bd`.
- `0x01be` `if-nez v1` branches to `0x01d4` unless previous state is **zero**.
- `0x01c0` `if-nez v3` branches to `0x01d4` unless incoming native state is **zero**.
- Only when both are zero does `0x01c4` invoke `okToConnect(device)`; after result conversion `0x01c8` `if-nez v4` goes to `0x01d4` on allow, otherwise calls device-address conversion at `0x01cc` and `access$600` at `0x01d0` (native-disconnect wrapper; name inferred from AOSP comparison, check accessor body separately).
- For accepted/non-initial cases the other side calls `access$700` and `access$100` at `0x01d6/0x01da` (state broadcast path).

This is **direct proof** that M3 performs a bond-state admission check on the **initial connected** HID state transition (previous 0, native state 0), not merely a generic method which may never be used. Android AOSP labels message code 3 `MESSAGE_CONNECT_STATE_CHANGED`, and its equivalent incoming-connected branch uses the same conditions; M3 bytecode supports the same semantics. This branch is downstream of actual native connection establishment: it does not solve earlier L2CAP auth. No device attempt performed.

References: https://android.googlesource.com/platform/packages/apps/Bluetooth/+/087d9f6a72a7f5ade938c2cbfb23aa01198bb85f/src/com/android/bluetooth/hid/HidHostService.java ; M3 uploaded APK SHA-256 above.
