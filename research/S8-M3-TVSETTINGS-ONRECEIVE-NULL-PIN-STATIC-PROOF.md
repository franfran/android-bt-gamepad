# S8 — Owner M3 TvSettings: receiver immediately invokes PIN branch with null

2026-10-31. Offline static analysis of owner-uploaded exact `/system/system_ext/priv-app/TvSettings/TvSettings.apk`; source was in `M3-TvSettings.apk.zip`. No M3 changes and no sensitive addresses/keys published.

## Crucial correction: DEX direct/virtual delta indices

Independent native Python DEX parser: enumerate `class_data_item` for `Lcom/android/tv/settings/bluetooth/BluetoothPairingRequest;`, reset `method_idx_diff` independently at the **direct_methods** and **virtual_methods** boundaries. Failure to reset gave a **false onCreate(Bundle)** association in one earlier update. Correct actual method entries:

- **direct** `onPair(int,java.lang.String)`: method_id **5404**, code_off **0x0eb65c**.
- **virtual** `onReceive(android.content.Context,android.content.Intent)`: method_id **5405**, code_off **0x0eb74c**.

The code offset 0xeb74c **is onReceive**, not onCreate. Supersedes the incorrect GitHub Issue #6 comment and earlier conversational report.

## Owner APK onReceive directly invokes onPair(variant,null)

The original code at 0xeb74c references:
- `android.bluetooth.device.action.PAIRING_REQUEST`;
- `android.bluetooth.device.extra.DEVICE`;
- `android.bluetooth.device.extra.PAIRING_VARIANT`;
- `android.bluetooth.device.extra.PAIRING_KEY`.

The `getIntExtra` call for `PAIRING_VARIANT` has its result moved into register **v6** (code unit 0x1d). At method tail, code units:
- `0x49: d37e` (instance field operation)
- **`0x4a: 0112`**, DEX `const/4 v1,#0` (null)
- **`0x4b: 3070; 0x4c: 151c; 0x4d: 0169`**, DEX `invoke-direct {v9,v6,v1}, method@0x151c`, where method@0x151c is `BluetoothPairingRequest.onPair(int,String)`.
- `0x4e: 000e`, return-void.

Hence receiver passes `onPair(pairingVariant, null)` in reachable tail route. The static proof does **not** alone establish the actual pairing variant for a specific runtime event.

## Owner APK PIN branch calls setPin(String)

`onPair` code at 0xeb65c has packed-switch payload at instruction index **0x56**, first key 0, size 7; the key=0 branch offset +0x35 from switch at instruction 0x1a, reaching **0x4f**. At:
- `0x4f/0x50`: load BluetoothDevice field;
- **`0x51: 206e; 0x52: 011b; 0x53: 0060`**, `invoke-virtual {v0,v6}, method@0x011b`, with resolved method `Landroid/bluetooth/BluetoothDevice;->setPin(Ljava/lang/String;)Z`; `v6` is `onPair`'s String argument `p2`.
- `0x54: 000e`, returns. The return value of `setPin` is not checked in this method.

Android API identifies **PAIRING_VARIANT_PIN = 0**; for this variant, a PIN should be provided by user or trusted application. https://developer.android.com/reference/android/bluetooth/BluetoothDevice

This makes a very concrete and strongly supported issue: **if** the broadcast's `PAIRING_VARIANT` is PIN=0 and the method reaches that call, it sends `setPin(null)`. However `setPin(null)`'s exact effect on M3 framework and whether that exact branch ran remain unverified by logcat; do not claim direct runtime proof of null reaching stack.

## Corroborating runtime evidence, independent of APK

Owner 2026-10-31 logcat:
- 11:54:23.556 `BluetoothBondStateMachine: pinRequestCallback: ... name:PLAYSTATION(R)3 Controller cod:508`
- 11:54:23.904 PID846 `BluetoothPairingRequest: onPair: null`
- 11:54:55.938 `BluetoothBondStateMachine: pinRequestCallback`
- 11:54:56.039 PID846 `BluetoothPairingRequest: onPair: null`

The PID846 process was `com.android.tv.settings`. Two separate interactions strongly corroborate the app received a pairing broadcast and called this onPair method with a null String. The log does not print variant or the returned boolean of `setPin`. Prior (different session) HCI traces showed 4 PIN Requests and no 0x040D/0x040E replies; they are **not** HCI evidence for these two newly logged attempts.

## Diagnosis priority and patch design caution

Most likely defective component: **TV Settings' Legacy PIN broadcast-handling branch**, not remote-name resolution. An implementation passing null for a PIN-type request cannot successfully provide DS3's required PIN. The next safe fix design should **not** automatically send a PIN based solely on an advertised BD_ADDR; for a DS3, use an owner-controlled USB enrollment or other authenticated trust gate, validate both device and incoming variant, then call the appropriate privileged API. Potential general fix for all devices: PIN variant must display/route to actual PIN entry UI instead of auto-submitting null. A separate DS3-specific flow could be designed only with owner authorization and rollback strategy.

Do not patch system APK, install privileged replacement, perform runtime injection, relax global Bluetooth security, or restart Bluetooth service. **S7 C4C-3 NO_GO remains.**

## Five evidence-based takeaways

1. Exact entrypoint is `BroadcastReceiver.onReceive` (not Activity onCreate)—previous correction was wrong due to DEX delta decoding.
2. Vendor `onReceive` reads pairing variant and directly calls `onPair(variant,null)`.
3. Actual `onPair` key0 (Android PIN variant) calls `BluetoothDevice.setPin(String)` with supplied arg (thus null if onReceive reaches key0).
4. Two real PIN callbacks followed by `onPair: null` from the same TV settings process corroborate route; no actual variant logged.
5. Response success/denial and modern DS3 path still need same-window HCI and/or runtime evidence; do not patch device until scoped design and approval.
