# I2/I6 — Native UHID vs Java admission ordering: source trace and strict offline gate

## Scope and pinned source

Pinned public source: \`BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d\`. This is **reference-source analysis and a host-only model**, not a built M3 patch, a security exception, or verified runtime behavior.

## Exact verified sequence and missing synchronization

1. [BTA: \`bta_hh_open_cmpl_act()\` at 513–561](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L513-L561): calls \`bta_hh_co_open()\` to initialize the UHID callout, **then** emits \`BTA_HH_OPEN_EVT\` (subject to protocol-mode branch). This callout opens \`/dev/uhid\` and starts its poll thread; it is **not** equivalent to creating a kernel HID device.
2. [BTIF: OPEN handler 772–815](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L772-L815): after native handle and fd checks, stores \`btif_hh_cb.p_curr_dev\`, calls \`BTA_HhGetDscpInfo(handle)\`, then sends the HAL \`connection_state_cb(address, CONNECTED)\`. This is an API-request/callback scheduling order, **not evidence that Java finishes admission before descriptor dispatch**.
3. [BTA: \`bta_hh_get_dscp_act\` 898–911](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L898-L911) can emit \`BTA_HH_GET_DSCP_EVT\`; [BTIF: 951–983](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L951-L983) uses the **shared mutable \`p_curr_dev\`** for this descriptor callback and immediately invokes \`bta_hh_co_send_hid_info(...)\`. In the examined path it does **not** verify that a protected event-bound Java admission token exists.
4. [UHID callout: 506–539](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L506-L539) writes \`UHID_CREATE\` including peer-reported descriptor/VID/PID into the kernel. No CablePairing descriptor-only allowlist is visible here.
5. [JNI: 54–70](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L54-L70) forwards address+state; [Java: 802–807](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L802-L807) **posts a Handler message**; [Java: 185–207](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L185-L207) later calls \`okToConnect()\` then possibly \`virtualUnPlugNative\`. There is no observed synchronous authorization barrier at the UHID creation point.
6. [Native report: BTA 606–622](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L606-L622) -> [callout 456–490](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L456-L490) -> [\`UHID_INPUT\` 292–305](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L292-L305): the existing \`ready_for_data\` flag is set by \`UHID_START/UHID_OPEN\` [co.cc:97–113](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L97-L113). **Kernel readiness is not Java policy approval**.

### Additional source review warning: cross-device descriptor association

The BTIF descriptor handler selects \`btif_hh_cb.p_curr_dev\` rather than an event-contained immutable HID handle/ACL generation. Multiple interleaved OPEN and GET_DSCP callbacks **could** point at a newer current device; whether the exact runtime scheduler makes a particular interleaving possible needs proof. This is a correlation hazard to test, not a claimed demonstrated exploit. An adapter must not rely on this shared pointer for security authorization.

## Strict model proposition, not an existing API

New host-only model \`experiments/m3-ds3-cable-session/uhid_admission_model.py\` gates a session \`(hid_handle, locally minted epoch)\`. It requires:

- Native cable policy already approved for **this** session (symbolic predicate only; real authorization remains unsolved).
- Validated gamepad-only descriptor for same ticket.
- Explicit **event-bound Java admission result** for same ticket (existing JNI callback **does not** provide this).
- Until both asynchronous events arrive, **no \`UHID_CREATE\`**. If Java denies, destroy candidate without creating HID device.
- After creation, kernel \`UHID_START/UHID_OPEN\` **plus** per-report validation are required before modeled \`UHID_INPUT\`. Close/reconnect revokes ticket.
- Normal already-bonded HID paths must be preserved by any later real integration; this model intentionally only describes hypothetical CablePairing candidate traffic.

Tests \`test_uhid_admission_model.py\` cover native denial, Java-before-descriptor, descriptor-before-Java, rejected descriptor, Java refusal, UHID ready != auth, report validation, reused handle stale descriptor, stale Java denial, concurrent handles and close/revocation.

## Verified offline results

From a local isolated Python 3.13.5 run of the two test modules:
\`\`\`text
python3 -m unittest -v test_mock_l2cap_btm test_uhid_admission_model
Ran 21 tests in 0.001s
OK
\`\`\`
- Earlier mocked BTM→L2CAP callback suite: **10/10 PASS**, now independently executed.
- New proposed strict pre-UHID admission suite: **11/11 PASS**.
- These results prove only deterministic **model behavior**; no Android HAL ABI, native source integration, radio authentication, concurrency, genuine descriptor parser or kernel security behavior has been exercised.

## Concrete implementation blocker and next proof

A real "Java result before UHID_CREATE" barrier needs a new protected event-bound authorization response path and **deferred descriptor handling**, while preventing deadlocks in the BTA/BTIF event loop and preserving non-cable bonded HID. Existing H618 code lacks that barrier. Alternately a fully native policy might gate pre-UHID creation, but then must independently address Java's later veto and input exposure; that design is also unproven.

Next source-first task: trace the BTA descriptor event structure and BTIF context handoff to see if immutable handle/epoch can be propagated without unstable HAL ABI changes, then evaluate a bounded proof-of-concept patch gated behind a disabled-by-default compile flag **only when matching BSP/build availability is established**.

**No M3 changes, no HCI operations, no blanket HID downgrade, no fake bond, no ABI change, no APK install, no PR #51 modification and no PR merge.**
