# I2/I6 — Native ↔ Java event-bound HID admission contract (host-only)

**Workstream:** Draft PR #52 (`research/m3-ds3-compat-adapter`). **Pinned public source:** `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`.

**Decision:** host-only event-bound admission contract PASS; Android JNI integration, unbonded DS3 security policy, and M3 wireless support remain **NOT IMPLEMENTED / NO_GO**. This is not an authorization to change HCI, BTM security, Java bonding, firmware or live device state.

## 1. Verified existing H618 source flow

| Layer | Pinned source | Current behaviour |
|---|---|---|
| BTIF | [`system/bt/btif/src/btif_hh.cc:772–815`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L772-L815) | On `BTA_HH_OPEN_EVT`, initiates `BTA_HhGetDscpInfo(handle)`, reports `CONNECTED` through `HAL_CBACK(connection_state_cb)`; descriptor response happens asynchronously. |
| JNI | [`packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp:52–71`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L52-L71) | JNI `connection_state_callback` calls `onConnectStateChanged(address,state)`, no request token or Java response; method ID is [`([BI)V`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L193-L200). |
| Java | [`HidHostService.java:185–216`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L185-L216) | `MESSAGE_CONNECT_STATE_CHANGED` is queued to a Handler. Java checks `okToConnect()` **after** the HAL sends `CONNECTED`, only on the specific `CONNECTED`/previously disconnected transition; if disallowed it requests `virtualUnPlugNative`. |
| Java policy | [`HidHostService.java:892–919`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L892-L919) | Existing `okToConnect` checks AdapterService available, quiet mode, `BOND_BONDED`, and allowed/unknown connection policy. The DS3 candidate is **not bonded** in owner evidence. |
| BTIF descriptor → kernel | [`btif_hh.cc:951–983`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L951-L983) | BTIF handles descriptor using shared `p_curr_dev` then calls `bta_hh_co_send_hid_info` toward `UHID_CREATE`, without waiting for a Java event-bound grant. |

**Source inference, not a demonstrated M3 exploit:** Native UHID creation could precede Handler rejection. The existing connected-state notification is not a safe approval request; no session generation or asynchronous Java acknowledgment crosses that callback.

## 2. Host-only original C++17 contract

Files:
- `experiments/m3-ds3-cable-session/java_admission_bridge.h`
- `experiments/m3-ds3-cable-session/test_java_admission_bridge.cc`
- `experiments/m3-ds3-cable-session/run_cpp_host_tests.sh` updated.

`JavaTicket = (HID handle, ACL epoch, Java service generation, request ID)`. Native creates a ticket on each new offer. An asynchronous Java reply is only accepted for **that exact ticket**; service stop/restart, new request on reused HID handle, disconnect, duplicate reply or replaced ACL epoch invalidates old tickets.

Separate Java result classes: `kAcceptStandard`, `kDeny`, `kCableReviewOnly`. Only **standard verified Native security + Java bond/policy approval + descriptor validation** can release the model's `UHID_CREATE`, once. A previously USB-enrolled controller claiming the correct MAC is at best `kCableCandidateUnverified`, and `kCableReviewOnly` has **no route to UHID_CREATE or UHID_INPUT**. The model also separately checks `kernel_ready` and `report_validated` before input.

`NativeEvidence::kVerifiedStandard` is a **symbolic input**, not a BTM proof. `JavaVerdict` values simulate replies, **not an implemented JNI call**. The model's boolean `java_connection_policy_allowed` represents existing allowed/unknown policy; it is not a substitute for retrieving the real AdapterService policy. The model intentionally does **not** implement a security exception for unbonded HID.

### Verification

Source files committed are byte-for-byte identical to the locally compiled files (verified using `git hash-object` for both exact files). Executed in isolated Linux host:

```text
g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
    test_java_admission_bridge.cc -o /tmp/bridge_test
/tmp/bridge_test
16/16 PASS (host-only event-bound Java admission)

g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    test_java_admission_bridge.cc -o /tmp/bridge_test_asan
ASAN_OPTIONS=detect_leaks=1 /tmp/bridge_test_asan
16/16 PASS (host-only event-bound Java admission)
```

16 **named host test scenarios**: service not started; standard bonded path with either Java-first or descriptor-first arrival; cable-review-only blocked; unverified cable candidate cannot impersonate bonded approval; quiet mode, unbonded and forbidden connection policy; explicit denial; duplicate reply; reused handle; repeated offer same ACL epoch; Java service restart; parallel devices; revoke before reply; stale revoke; report/kernel input gates; invalid inputs. These tests do not use Android, hardware, radio authentication or real DS3 descriptor bytes.

## 3. Source integration contract, not a patch

A future **feature-disabled** implementation in the exact target-compatible source should use:

1. **Native source of truth for session ticket:** mint at a stable ACL/HID lifecycle point with appropriate locking/serialization; never derive it solely from MAC, HID handle, LCB/CCB pointer. Current PR #52 ACL observation epoch is **not** a cryptographically trustworthy or immutable end-to-end reference.
2. **Separate internal asynchronous JNI method** to Java `HidHostService`, e.g. conceptual `onRetroboxCandidate(address,handle,aclEpoch,requestId,javaServiceEpoch)`; the concrete JNI signature, 64-bit treatment, thread ownership and error semantics must be established in source. Do **not** repurpose `onConnectStateChanged([BI)V` or change public HAL ABI.
3. **Java Handler decision** bound to exactly that native request and Java service lifetime. Standard bonded HID should continue existing `okToConnect` flow unaffected. For cable candidates, Java can record `candidate/review-only`, but **must not claim BOND_BONDED**, bypass its existing quiet mode/policy rules, or grant input until separately approved genuine Native security compatibility and owner-risk scope exist.
4. **Dedicated Native response function** that rejects a stale ticket and checks both Native security policy and Java decision. Callbacks can race with disconnect, Java service restart and descriptor delivery. Never block the JNI callback thread waiting synchronously for Java Handler (deadlock risk). Timeout/failed post/service shutdown must cancel ticket and free descriptor bytes.
5. **Before any candidate UHID_CREATE:** validate the real descriptor, correlate per-device exact handle+epoch with owned descriptor bytes, then accept only approved Native+Java state. **Before UHID_INPUT:** validate report and kernel readiness; revoke on disconnect.
6. **Legacy preservation:** default-off research macros; normal bonded HID devices use unchanged flow. No global HID PSM security downgrade, forged LinkKey/HCI success, fake bond or MAC-only exception.

### Why this is not yet a working DS3 Bluetooth patch

The owner-provided M3 capture still reports HCI auth timeout `0x22` and `BOND_BONDING → BOND_NONE`. USB `sixpair` already wrote the adapter address; BlueZ-guided F2/F5 transaction work on PR #52 is **only enrollment modeling**, not a resolution to the Bluetooth controller authentication. There is **no proven Java admission of an unbonded controller, no actual JNI response implementation, no target-compatible Android BSP build** and no authorized runtime experiment.

**Next proof gate:** source-level candidate event/JNI response interface implementation sketch, with concrete status-handling, ownership and service lifecycle; separate test of ordinary bonded HID unaffected. Real target work stays NO_GO pending full source and explicit scoped owner review.
