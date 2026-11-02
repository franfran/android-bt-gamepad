# I2 — Historical PIN / timeout evidence and causal limits

Status: offline historical-document review only. Updated from PR #50 documents, not from a new live controller capture.

## Evidence
- [PR #50 pairing implementation plan](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-PAIRING-IMPLEMENTATION-PLAN.md) records historical HCI PIN requests with no reply followed by timeout. It explicitly says the runtime `min16Digits` / pairing variant for **those attempts** was not directly observed.
- Same PR #50 document reports OEM TvSettings APK `BluetoothPairingRequest.onReceive()` -> `onPair(variant,null)`; PIN variant 0 passes null through `BluetoothDevice.setPin(String)`, which actual M3 framework rejects. This is a *real OEM policy defect*, but a binding to the specific historical HCI timeout cannot be inferred without synchronized raw events.
- [PR #50 preauth proof](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-PREAUTH-PEER-PSM-PROOF.md) provides incoming peer/PSM context and a **static** HCI auth request path, not a live per-connection native stack execution trace.
- [PR #50 UHID gate](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-KERNEL-UHID-SETREPORT-GATE.md) establishes the OEM standard UHID SET reply deficiency but **no observed live wireless reachability**.

## Critical hypothesis boundaries
A. `HCI status 0x22 = LMP_RESPONSE_TIMEOUT` is observed in historical work, but it is not equal to explicit `AUTH_FAILURE 0x05`.
B. Missing PIN reply may contribute to a particular legacy pairing timeout, yet the source record does **not** establish same-attempt causal order with 0x22. Do not claim root cause proven.
C. USB report 0xF5 sixpair enrollment sets controller host address; it is NOT itself a Bluetooth link key or proof of remote authenticity. Prior Mac zero-length PIN behavior does NOT prove Android can send it, nor that DS3 accepts it.
D. Source-only Java `okToConnect` and OEM corroboration show later bond gate; that gate has not been observed on a successfully native-connected wireless DS3 attempt.
E. No generic PIN 0000, MAC-as-PIN, or fabricated link key shall be proposed.

## Distinguishing evidence matrix
| Question | Existing evidence | Needed to close |
| --- | --- | --- |
| Same attempt: PIN request -> missing reply -> 0x22? | Separate historical summaries | Monotonic timestamp + same ephemeral session ID for HCI PIN Code Request/Reply, Authentication Complete, disconnection |
| Is PIN handler variant 0 active for that DS3 attempt? | OEM null input call path | Exact per-attempt variant / min16Digits and whether any handler responded |
| Does 0x22 arise despite valid PIN response? | No | Historical success/failure comparison or future separately approved passive capture |
| Is nonbonded DS3 Classic HID authorized safely? | No | Proven identity/enrollment and per-device security contract; no spoofable MAC-only bypass |
| Does Java virtual-unplug happen? | Conditional code only | Correlated connected-state Java event (no new live test authorized) |
| Is UHID SET reached? | OEM binary callback deficit | Correlated kernel/HID event evidence |

## Engineering next decision
Do **not** begin adapter code now. First audit whether historical artifacts preserve one continuous timestamped HCI transaction, and classify missing pieces. If unavailable, prepare a *separately approved, passive, bounded capture plan* targeting **one** intentional pairing attempt; no system changes, PIN injection or Bluetooth restart. If existing evidence becomes sufficient, skip capture. A privileged PIN-helper alone is insufficient without native security/Java gates.

## Safety
Research-only Draft PR #52; PR #50 and #51 remain separate. No device commands, link-key or bond database modification, security weakening, firmware swap, injection, or pairing attempt.
