# M3 DS3 Control/Interrupt association: offline test and reference-implementation evidence

**2026-10-31. Read-only/offline.** Existing implementation in `experiments/m3-cable-policy/dual_channel_policy.py` and `test_dual_channel_policy.py` was fetched from PR #50 and reproduced unchanged in a local Python 3 test environment. Result:

```
python3 -m unittest -v test_dual_channel_policy
Ran 9 tests in 0.001s
OK
```

Tests cover control (PSM 0x11) then interrupt (0x13), duplicate control, interrupt-before-control, unknown peer/host, wrong PSM or transport, unauthorized/revoked session, expiry, and no fabricated bond/authenticated state. **This is a source-only test, not an M3 Bluetooth live test.**

## Upstream control-first requirement corroborated

AOSP Fluoride Host `hidh_l2cif_connect_ind` checks that incoming interrupt PSM has an existing control CID and the state is `HID_CONN_STATE_CONNECTING_INTR`. If either condition fails, it rejects the second connection. On incoming control PSM, it stores the control CID and advances to `HID_CONN_STATE_CONNECTING_INTR`. Android source:
- https://android.googlesource.com/platform/system/bt/+/043dce2c07dac9f108e5094d8ec9df6a65e50fb3/stack/hid/hidh_conn.cc
- https://android.googlesource.com/platform/packages/modules/Bluetooth/+/1fdde1b31884edd37d0348db6f6ebb390aebc947/system/stack/hid/hidh_conn.cc

These are reference implementations and support the model's **control-first protocol assumption**, but the precise branch behavior must still be confirmed against original M3 `hidh_l2cif_connect_ind` instructions or live traces, not automatically declared identical.

## More important correction: candidate channels ≠ usable HID

The prototype's `complete(session)` means **two PSMs registered as offline candidates**, not two negotiated L2CAP channels, not `HID_CONN_STATE_CONNECTED`, and not valid Android InputDevice reports. The actual stack further configures both channels, sets connected state only after relevant configuration completion, and then passes the native/Java HID admission gates. A policy guard must not signal operational success from two candidate requests.

In a future version rename `complete` to `candidate_pair_seen`, or add distinct states for `L2CAP_PENDING`, `CONTROL_CONFIGURED`, `INTERRUPT_CONFIGURED`, `NATIVE_CONNECTED`, `JAVA_ADMITTED`, `INPUT_DEVICE_READY`. Do not treat any of these as equivalent.

## Security boundary

An owner-authorized USB enrollment is a local policy input; matching a controller MAC or token is not cryptographic identity. No global security mask relaxation, fake bond, disabled encryption for unrelated devices, or live process injection is justified. The actual hardware authentication failure `0x22` remains unexplained.

## Recommended next task

Refine the **offline-only state model** to separate candidate admission from channel configuration and final HID/Android InputDevice readiness; test disconnect/reconnect and session reset. Then assess which exact native and Java callbacks could report those states without changing M3. Keep PR #50 draft and C4C-3 live NO_GO.

## Later verification on October 31, 2026

Re-fetched **both exact PR #50 test source files** for the dual-channel policy and readiness tracker, reproduced them in an isolated local Python 3 environment, and executed:

```sh
python3 -m unittest -v test_dual_channel_policy test_readiness_model
```

Result: **18 tests, all PASS**, no failures/errors (9 dual-channel + 9 readiness). This only validates the offline simulations. The readiness tracker accepts programmatic state transitions; it does **not** receive authenticated events from M3 nor protect against stale callbacks across actual device sessions. The next observer model must include session correlation/epoch, explicit event provenance, and disconnect/error invalidation before it could be considered useful telemetry. **Do not use `Readiness.operational()` as an authorization signal or real wireless success evidence.**

Separate original-APK verification of the M3 `convertHalState` mapping and `virtualUnPlugNative` rejection chain was also performed read-only; see `docs/M3-DS3-HID-DEX-AND-NATIVE-GATES.md`.
