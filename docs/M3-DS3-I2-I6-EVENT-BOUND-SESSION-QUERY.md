# I2/I6 — Private session query: lifecycle, source owner and explicit NO_GO boundaries

Pinned H618 tree: `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. Design research only; no Android/M3 code changes.

## New trace: why querying by address inside Java is not enough
- [BTIF HID event dispatcher: btif_hh.cc 772–830](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L772-L830): successful `BTA_HH_OPEN_EVT` only reaches `connection_state_cb(...CONNECTED)` after device-handle lookup, UHID file descriptor presence and descriptor-info request. Failed opens produce `DISCONNECTED` callback.
- [BTIF close handling: btif_hh.cc 834–858](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L834-L858): closes UHID fd, emits `DISCONNECTED`; locally initiated virtual unplug may call `BTA_DmRemoveDevice`. Cable-enrollment record MUST NOT be implicitly mapped to ordinary Android bond DB or removed/forged through bond operations.
- [JNI:54–70](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L54-L70) passes only `address,state`, with no BTA HID handle/ACL generation.
- [Java:185–207](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L185-L207) processes posted connected message later on its handler, then conditionally executes `okToConnect` and VUP. A protected query keyed solely by address at handler time can see a **newer** connection after the earlier callback: classic time-of-check/time-of-use race.

## Minimum *conceptual* interface
A **versioned, internal, privileged-only** query should bind the event to a unique native connection epoch captured **at event emission**, not by re-looking up current address later. Example abstract contract (NOT actual Fluoride API):
- Input: `{controllerHandle, transport=BR_EDR, aclGeneration, hidGeneration, expectedEvent=CONNECTED, enrollmentGeneration}`.
- Output: `{decision=ALLOW_CABLE|DENY|STALE, grantGeneration, expiry, controlAndInterruptVerified, policyReasonCode}`.
- This is a proposed contract; existing JNI method `([BI)V` and HAL HID callback cannot carry these fields.
- No public broadcasts, no arbitrary app-supplied identity, no false link authentication/encryption, no generic `BOND_BONDED` mutation.
- **Critical unresolved dependency:** ordinary DS3 cable enrollment may have no cryptographic radio peer authentication. A native epoch prevents stale/replay races but **does not prove a spoofed MAC is really the physically enrolled DS3**. If acceptable risk cannot be bounded and explicitly approved, **NO_GO**.

## Session owner and lifecycle
- Long-lived private enrollment owner (proposed): privileged system Bluetooth component owning USB physical-enrollment event, adapter/version provenance, generation, explicit revocation; persist only minimal metadata in appropriately protected private storage. Ownership/storage API remain unproven.
- Ephemeral session owner (proposed): native Bluetooth-side registry deriving epoch on new ACL connection and advancing only after independently verified controller/PSM eligibility; expire on link teardown, device/service reset, revocation, host adapter change, timeout, out-of-order HID control/interrupt or simultaneous conflicting handles.
- BTIF BTA HID open is **not** the point where trust is established; it is a later observation after native gates and may already have UHID fd/descriptor work.
- Java may consume only the immutable event-bound capability and must still check quiet mode, forbidden connection policy, expiry and exact epoch. On stale or missing grant, preserve ordinary denial behavior.
- Reset/cleanup/boot: ephemeral records cleared; persisted owner-enrolled record requires revalidation before any fresh wireless session. Wireless reconnect should not require repeating USB cable setup.

## Required host-only negative tests
1. CONNECTED event for session A queued; A disconnects; same BD_ADDR session B created before Java handles A event -> A MUST reject as STALE.
2. CCB pointer/BTIF device handle reused after disconnect -> old epoch cannot grant new link.
3. Grant revoked between native event and Java consumption -> reject; repeated query cannot reauthorize.
4. Only one HID PSM present, mixed controllers or interrupt-only -> deny or defer based on verified ordering; never claim HID ready.
5. `BTA_HH_OPEN_EVT` success but no valid query grant -> Java rejects; no false wireless success.
6. LOCAL VUP / `BTA_HH_CLOSE_EVT` -> close ephemeral grant; never delete persistent enrollment as though it were Bluetooth bond state.
7. Existing normal bonded Bluetooth HID -> untouched default code path; non-HID profiles unaffected.
8. Unknown/spoofed radio controller -> do not claim cryptographic authentication based on address/name/CoD.
9. Process death, startup, device reboot -> no prior volatile grant survives.

## Minimum-change verdict
A query-only API by peer address is **NO_GO** because callback lacks event-bound generation and Java handler is asynchronous. Adding attributes to ABI structs without matched OEM HAL/JNI build proof is **NO_GO**. Proper approach requires source-integrated *event-bound generation propagation* plus protected lookup/consumption, or a separately established supported mechanism. This may span L2CAP/BTM, BTA/BTIF, JNI, Java and later UHID; not a one-.so replacement.

Owner baseline: DS3 wired USB RetroArch already working; one-time physical USB setup acceptable; normal use wireless without cable or re-enrollment.

**No implementation, pairing attempt, service restart, native injection, security weakening or M3 operations authorized.**
