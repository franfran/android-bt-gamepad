# S8: M3 Remote Name Timer Timeout Dispatches Registered Completion Callback

**Offline original-owner ELF verification** — M3 ARM32 `libbluetooth.so` SHA256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`; original ELF VMAs; Thumb. Read-only. Extends Draft PR #45.

## Decisive correction to the name-stall theory

The original mini-debug symbol table identifies `btm_inq_remote_name_timer_timeout(void*)` at `0x24c7d8`, and `btm_process_remote_name(RawAddress const*,uint8_t*,uint16_t,uint8_t)` at `0x24c5f8`.

The **actual timeout function instructions**:
- `0x24c7f8: ldrb.w r0,[r4,#0x296]`: check active remote-name request flag.
- `0x24c7fc: cbz r0,0x24c80c`: no active request, skip.
- `0x24c7fe: add.w r0,r4,#0x290`: take pending peer address.
- `0x24c802: movs r1,#0`, `0x24c804: movs r2,#0`, `0x24c806: movs r3,#0x1f`: no name, zero length, timeout error.
- `0x24c808: bl 0x24c5f8`: call `btm_process_remote_name(...,status=0x1f)`.

The **actual processor**:
- `0x24c622: ldr.w r8,[r9,#0x278]`: load stored completion callback.
- `0x24c726: ldr.w r0,[r9,#0x27c]`, `0x24c72a: bl 0x2b1094`: cancel remote-name timer.
- `0x24c734: strb.w r0,[r9,#0x296]` with r0=0: clear active flag.
- `0x24c784: str.w r2,[r9,#0x278]` with r2=0: clear stored callback.
- `0x24c798..0x24c79e`: if callback ptr in r8 nonzero, invoke it using `blxne r8`. The function creates a status/event buffer before dispatch.

PR #45 independently identified the callback supplied by the BTA PIN missing-name route: `bta_dm_pinname_cback` at `0x137e08`. That callback can dispatch a PIN event with empty name if the BTA security callback is registered.

Thus **the M3 binary contains a positive error/timeout completion route**. An HCI Remote Name Request accepted without a matching successful Complete does **not by itself prove an indefinitely missing PIN event**: if the software timer fires while that request and callback are active, the stack can notify the waiting BTA PIN callback with an error.

## Critical remaining uncertainties

- Whether the request was still active in global `+0x296` on the DS3 pairing attempt.
- Whether `+0x278` still held the BTA PIN-name callback at timeout or had been replaced/cleared by another request.
- **Actual timer delay**, start/cancellation order, and whether the timer event occurs before the HCI authentication timeout (~30.06 sec).
- Whether BTA callback is registered and pending pairing state persists until the callback.
- Whether BTA event reaches BTIF/Java, or is rejected as a non-user-initiated pairing request.

The captured btsnoop does not contain host software timers, callback invocations, or Java pairing decisions. Remote-name commands #561/#578 predate the four PIN requests, so attributing all four missing HCI PIN replies to a stale remote-name inquiry is especially weak without matching runtime logs.

## Next most useful work

1. Trace **remote-name timer scheduling and its exact duration** in `BTM_ReadRemoteDeviceName`, and compare host timer expiration against four actual HCI PIN timestamps.
2. Map `BTA_DM_PIN_REQ_EVT` → BTIF `btif_dm_pin_req_evt` → Java pairing request handling and possible policy-suppressed legacy PIN callback. Find the last verified boundary using platform logs if available.
3. Avoid global PIN automation or bypass. Any DS3-specific exception needs owner-controlled USB enrollment and a separately approved reversible recovery gate.

**No device changes. No original captures or Bluetooth MAC/PIN committed. S7 C4C-3 injection NO_GO.**
