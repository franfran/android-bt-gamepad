# I2/I6 — Event-bound Native → Java HID admission contract (host-only)

**Workstream:** RetroBox M3 DS3 wireless, Draft PR #52, branch `research/m3-ds3-compat-adapter`. Pinned H618 reference source: `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. Source derived facts and proposed changes are separated below.

**Current result:** An original Java-only admission *contract model* plus 48 strict host assertions. No source modifications to H618 Java, JNI, BTIF, BTA, BTM, or M3 were made in this increment. The USB enrollment work from the preceding increment stays host-only. Normal wired DS3 RetroArch input is owner-verified; wireless remains unsuccessful.

## Source-proven callback/order problem

1. [`btif_hh.cc:772–815`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L772-L815) on `BTA_HH_OPEN_EVT` sets the shared `p_curr_dev`, requests `BTA_HhGetDscpInfo(handle)`, then invokes the HAL `connection_state_cb(...CONNECTED)`.
2. [`btif_hh.cc:951–983`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L951-L983) on the asynchronous descriptor event immediately calls `bta_hh_co_send_hid_info` → `UHID_CREATE`. This is not tied to a Java approval result, and shared `p_curr_dev` is not an immutable descriptor/session ID.
3. [JNI `com_android_bluetooth_hid_host.cpp:53–72`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L53-L72) calls Java `onConnectStateChanged(byte[], int)`, looked up with signature **`([BI)V`** at [line 195](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L194-L195). It carries **address and state only**—no HID handle, ACL epoch, boot identity or Java admission response.
4. [`HidHostService.java:802–808`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L802-L808) enqueues `MESSAGE_CONNECT_STATE_CHANGED` to its Handler. [Handler:185–207](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L185-L207) invokes `okToConnect()` on *connected* state, then calls `virtualUnPlugNative` on refusal. This may occur **after** Native UHID creation. It is not a pre-UHID grant.
5. [`okToConnect:892–919`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L892-L919) rejects if AdapterService is unavailable, quiet-mode disallows, nonbonded, or connection policy forbids. It has no cable-pairing trust state.

**Consequence:** A new DS3 path cannot be implemented by modifying the existing address-only `onConnectStateChanged`, faking `BOND_BONDED`, or treating a USB-F5 host-address write as native authorization. An **internal, earlier, event-bound request/response** is required *if a future safe and scoped exception is ever designed*. The stock HAL callback ABI should remain unchanged for normal HID.

## New offline Java admission coordinator

Files:
- `experiments/m3-ds3-cable-session/Ds3AdmissionCoordinator.java`
- `experiments/m3-ds3-cable-session/TestDs3AdmissionCoordinator.java`
- `experiments/m3-ds3-cable-session/run_java_host_tests.sh`

The Java-only class has no Android imports. It captures a simulated immutable `Ticket(bootId, HID handle, ACL epoch)` and a defensively copied 6-byte address. Only a **trusted Native implementation** could mint a genuine boot/session ticket and attest `NORMAL_AUTHENTICATED_HID`; this class has no such functionality.

A Java Handler-like `evaluate(event, policy)` must re-check quiet mode, connection policy and bond state, and it **always rejects** `USB_ADDRESS_CANDIDATE` without regard to owner approval or MAC match. A separate `receiveReply` accepts only the exact current event instance, same ticket, and a response matching the most recently evaluated decision. Duplicate responses, un-evaluated forced `ALLOW`, stale epochs and previous native-service boot IDs are refused. `permittedBeforeUhidCreate` is a **symbolic Boolean**, not an Android kernel call.

An approved reply is **only modeled for normal authenticated and bonded HID**. The class deliberately has no path to make the desired nonbonded DS3 wireless exception work. That remains an outstanding trust/policy decision, not a missing flag.

### Host test evidence

The exact original class/test source was compiled under `javac 21.0.12.1 -Xlint:all -Werror` and executed in an isolated Linux host JVM:

```text
javac -Xlint:all -Werror -d . Ds3AdmissionCoordinator.java TestDs3AdmissionCoordinator.java
java retrobox.TestDs3AdmissionCoordinator
48/48 PASS (Java host-only event-bound admission)
```

The 48 are **assertions**, not independent Android integration cases. They cover normal bonded admission, cloning address arrays, Java policy refusal, USB-candidate-only denial, no pre-reply UHID allowance, duplicate/stale replies, per-handle epoch monotonicity, handle reuse, native restart boot mismatch and malformed inputs. No JNI, Java Android framework, Bluetooth, USB, `UHID_CREATE`, or M3 test was run. A shell runner is committed, but a full Android compilation has **not** been performed.

## Proposed private JNI bridge contract (NOT IMPLEMENTED)

This is architecture only, **not** an existing JNI method/signature in the pinned source:

1. **Native request source:** before candidate-specific `bta_hh_co_send_hid_info` and input delivery, mint a request-bound opaque ticket with boot generation, live ACL/HID session epoch, device handle and descriptor ownership. Do not derive it from `p_curr_dev` or MAC. Normal bonded devices must retain existing behavior.
2. **Private JNI → Java request:** deliver `(address copy, bootId, HID handle, ACL epoch, evidence class)` to `HidHostService` on an appropriate Handler without blocking the Bluetooth/JNI callback thread. Existing `([BI)V` connection state callback remains intact. The new callback would require explicit registration, native ownership and lifecycle proof.
3. **Handler evaluation:** preserve AdapterService availability, quiet mode, bond state, connection policy. For USB-only candidate, **return deny pending a separately approved bounded-risk design**, not an unconditional allow.
4. **Java → native reply:** send the decision together with unchanged ticket identifiers. Native must validate request still active, ACL generation unchanged, matching descriptor, no disconnect/service-restart, and no later Java-policy revocation **before UHID_CREATE and each UHID_INPUT**. On timeout, denial, app shutdown or queue post failure, release owned descriptor, retire ticket, reject input.
5. **Do not block** waiting for a Java Handler response on the same execution thread that has to deliver it. Model both Java-first/descriptor-first event ordering. Define actual message scheduling, timeout and lifecycle cleanup before source integration.

**Known limitations:** The model does not prevent a real Java policy from changing *after* an earlier positive evaluation; a real implementation needs policy-change cancellation and a final check at the native UHID boundary. All policy/evidence values are simulated booleans/enums and thus are **not attested**. The M3 HCI authentication timeout 0x22 occurs upstream of this Java handler and is **not fixed** by the coordinator.

## Engineering decision

**GO** for deeper offline research of private JNI admission ordering and trusted M3-local USB enrollment evidence. **NO_GO** for nonbonded HID security relaxation, Android Java/JNI code changes in production, live M3 experiments, enabling old BTM research patches, assuming request ref pool capacity is adequate, target `libbluetooth.so` build/replacement, or PR merge. PR #50 reverse-engineering archive and PR #51 source-first BSP work remain separate.

For the next increment, source-audit whether the standard DS3 authentication route can be made compatible *without* an exception, and document exactly what would be required to prove an owner-present USB session from Android's privileged USB backend. Do not use MAC matching as proof.
