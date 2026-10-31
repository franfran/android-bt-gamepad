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
