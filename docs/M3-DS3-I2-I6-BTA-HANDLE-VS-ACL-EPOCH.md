# I2/I6 — HID Handle Correlation: BTA to BTIF, missing ACL epoch

Pinned H618 source `250eabfc529518b7f26432663ed0a867ab2f625d`. Research only.

## Verified edges
- [BTA HH state dispatcher](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_main.cc#L187-L258) constructs `tBTA_HH` callback unions, including `conn.handle` in open and `dev_status.handle` in close event shapes.
- [bte_hh_evt context transfer](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1095-L1133) copies the event payload into BTIF task context: `sizeof(tBTA_HH_CONN)` for OPEN, `sizeof(tBTA_HH_CBDATA)` for CLOSE.
- [BTIF HH open/close](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L772-L858) uses BTA HID handle to look up the connected device, but calls HAL `connection_state_cb` with **only address and state**, dropping that handle.
- [JNI callback](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L54-L70) delivers only address and state to Java `onConnectStateChanged([BI)V`. Java queues that callback before performing the admission test.

## Critical distinction
BTA HID `handle` is *not* proven to be the controller's HCI ACL handle or a lifetime-unique session generation. Its presence can help track HID open/close **within BTIF**, but it cannot independently authenticate a radio peer, persist across reconnect, or close the Java queue TOCTOU hole. The callback payload lacks a monotonic ACL/HID epoch and the relationship between BTA handle reuse and ACL generation is still unverified.

## Narrow next-stage host-only proposal
A future source-integrated proof could attach an internally minted generation at the earliest verified ACL-to-HID binding, carry immutable {generation, BTA HID handle, enrollment generation, adapter epoch, peer routing key, state} alongside an event, and have Java consume a protected one-shot grant only for the **exact emitted event**. Require validation across close/reopen, service restarts and callback queuing. Existing HAL `bthh_callbacks_t` and JNI signatures are unmodified here; whether a separate same-process query or parallel callback is safe/buildable is **unproven**, not assumed.

## No-rework and fail-closed tests
- Close session A; open B using same BTA HID handle and address; delayed A callback **must not** authorize B.
- HID open callback after ACL teardown; no persistent enrollment-based instant allow.
- HID device handle valid but Java event has no matching immutable grant; reject.
- BTA close can invoke `BTA_DmRemoveDevice` on locally initiated VUP: cable-enrollment must be separate from Android bond database.
- Keep ordinary bonded Bluetooth HID and unrelated profiles unchanged. No name/MAC/CoD-only trust.
- Owner acceptance: already-working wired USB RetroArch, USB setup once, then wireless DS3 gameplay after reconnect/reboot without recurring cable.

**Verdict:** BTA→BTIF handle transport VERIFIED; ACL epoch preservation through HAL/JNI NOT PRESENT in examined path; secure source-integrated authorization bridge still implementation NO_GO. No M3 operations.
