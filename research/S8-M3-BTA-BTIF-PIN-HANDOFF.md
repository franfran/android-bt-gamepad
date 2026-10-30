# S8 — BTA → BTIF PIN Event Handoff in the Original M3 Bluetooth ELF

2026-10-29. This document extends Draft PR #43 from native BTM up through the BTA device manager and the lower portion of the BTIF reply layer. **Original owner-provided M3 ELF** SHA-256: `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`. Addresses below are original ELF Thumb VMAs; vendor symbol names are resolved from decompressed `.gnu_debugdata`, **not** from the incorrect nearest-symbol labels printed by llvm-objdump on the stripped library. Entire analysis is static and offline.

## Critical raw-HCI evidence (supersedes pre-PR #43 description)

In the full owner-uploaded btsnoop, four distinct DS3 pairing attempts receive controller **PIN Code Request**, but **neither** HCI PIN Code Request Reply `0x040D` nor HCI PIN Code Request Negative Reply `0x040E` is emitted. Authentication Complete `0x22` appears ~30.06s later. The former claim of a 6-byte PIN Reply was mistaken; no PIN byte-order inference is possible because **no PIN reply exists** in the capture.

## NEW: BTA PIN callback registration, name gate, and asynchronous branch

The original mini-debug symbols identify:
- `bta_dm_pin_cback(RawAddress const&, uint8_t*, uint8_t*, bool)`: **0x137394** (size 240).
- `BTA_DmPinReply(RawAddress const&, bool, uint8_t, uint8_t*)`: **0x138ce4** (size 200).
- `bta_dm_pin_reply(unique_ptr<...>)`: **0x1344c8** (size 76).
- `btif_dm_pin_reply(RawAddress,uint8_t,uint8_t,bt_pin_code_t)`: **0x1cf1a4** (size 272).
- `invoke_pin_request_cb(RawAddress,bt_bdname_t,unsigned int,bool)`: **0x1a9514** (size 144).

Original exact assembly of `bta_dm_pin_cback`:

```asm
0x1373c2: ldr.w r0,[r6,#0xb0]     ; BTA security event callback pointer
0x1373c6: cbz r0,0x137406        ; unregistered: returns 0x0b; no dispatch
0x1373c8: ldrb.w r0,[r10]        ; initial remote-name byte
0x1373cc: cbz r0,0x13740a       ; name missing: deferred branch
...
0x1373f4: ldr.w r2,[r6,#0xb0]    ; registered callback
0x1373f8: movs r0,#2            ; BTA_DM_PIN_REQ_EVT value is 2
0x137400: blx r2                ; dispatch BTA PIN event (named branch)
...
0x13740e: strb.w r0,[r6,#0x1a9] ; no-name branch marks state = 2
0x137418..0x137430: stores remote address/class into pending globals
0x137438: bl 0x24b804         ; initiates deferred processing
```

**Interpretation:** Even when native BTM calls `bta_dm_pin_cback`, the request may not immediately reach BTIF if (a) the BTA callback is unregistered or (b) the remote name is missing and the asynchronous name path does not finish. The code demonstrates these paths exist; raw HCI cannot tell which, if any, happened in the DS3 session. The precise callee at 0x24b804 and its completion/error behavior still need independent evidence.

AOSP reference `BTA_DM_PIN_REQ_EVT = 2`:
https://chromium.googlesource.com/aosp/platform/system/bt/+/3d6accfcc0bdc5c7a8713320c9bb069cbf253348/bta/include/bta_api.h

## NEW: BTIF response gate before BTA reply

Original ELF `btif_dm_pin_reply` at **0x1cf1a4** branches on a byte at a BTIF global base `+0x19`:
- At `0x1cf1f6`: `ldrb r0,[r6,#0x19]`.
- At `0x1cf1f8`: `cbz r0,0x1cf26c`. For zero, at `0x1cf27a`, it invokes `BTA_DmPinReply` **0x138ce4**.
- For nonzero, it performs an **alternative PIN/passkey conversion path** before calling `0x139318` at `0x1cf266`. AOSP uses a corresponding `pairing_cb.is_le_only` distinction between LE passkey and Classic PIN reply; it is plausible this is that flag, **but this vendor global offset's exact name is not proven from ELF alone**.

Original `BTA_DmPinReply` `0x138ce4` is a short wrapper building an asynchronous BTA message with address, accept, PIN length and PIN bytes. It does **not** directly issue HCI `0x040D`: eventual BTA and BTM handlers must process the queued reply. Thus, even if a future upper-layer callback attempts a PIN reply, the actual HCI command still requires the correct BTA/BTM pending state.

AOSP reference for the analogous BTIF source (cross-check, not a claim that the vendor binary matches it identically):
https://android.googlesource.com/platform/packages/modules/Bluetooth/+/fb790450b5/system/btif/src/btif_dm.cc

## Hypotheses in strict priority order

| Boundary | Confirmed in original ELF? | Captured on actual DS3 runtime? | Practical observation needed |
|---|---|---|---|
| BTM receives controller PIN request | yes (existing handlers) | yes (HCI event only, not code execution) | already have HCI evidence |
| BTM invokes BTA callback | callback path exists | **unproven** | timestamped native logcat markers |
| BTA security callback pointer exists | explicit null guard at 0x1373c2 | **unproven** | logcat / initialization evidence |
| BTA has usable remote name or completes name query | name async branch proven | **unproven** | name request/complete, BTA DM logs |
| BTIF PIN event arrives | AOSP source route exists | **unproven** | `btif_dm_pin_req_evt`, `BTA_DM_PIN_REQ_EVT` markers |
| Java receives pairing request and responds | platform API route exists | **unproven** | filtered Android logcat/BondStateMachine history |
| BTIF/BTA reply queued and reaches BTM | reply wrapper in ELF | **unproven** | `btif_dm_pin_reply`/ `BTA_DmPinReply` logs |
| Controller receives HCI positive/negative PIN reply | both builders exist | **NO**: zero observed | absence already proven by raw btsnoop |

**Do not collapse these into a claim that Java necessarily dropped the PIN.** Another legitimate outcome is BTA's missing-name deferred process, and the callback might be absent or the response rejected by pending state.

## Follow-up strategy and safety

1. Prefer existing BTIF/BTA logcat or dump from the **same timeframe**. Seek names `BTA_DM_PIN_REQ_EVT`, `btif_dm_pin_req_evt`, `BTM_PINCodeReply`, `BondStateMachine`, `PIN_REQ` without printing BT addresses or PIN.
2. Offline analyze whether the name-resolution request at `0x24b804` and its completion path can stall. Identify exactly which callback it must reach and check existing btsnoop for name-related HCI commands/events and their timing before claiming it stalled.
3. Trace AOSP / vendor JNI pairing callback path only insofar as evidence supports it; do **not** implement a speculative global auto-PIN / MAC-only allow rule.
4. All on-device injection, restarts, vendor `.so` replacement, firmware modification and global HID security mask `0x36` reduction remain **NO_GO**. No new wiring or USB baseline testing needed.

**Bottom line:** A distinct, concrete candidate for missing PIN reply is now identified **inside BTA**, including an explicit unregistered-callback guard and a remote-name asynchronous path. This is further upstream than the previous BTM event and deserves differential investigation against HCI remote-name traffic and platform logs.


## NEW cross-check: *actual HCI capture* remote-name transactions for the DS3

Independently parsed the 1,789-record `btsnoop_hci(1).log` as HCI UART H4, using raw *six-byte address comparison only in local memory*, never reporting addresses:

- Four PIN Code Request events (`#595, #638, #1655, #1755`) correspond to **the same DS3 peer**.
- Exactly **two HCI Remote Name Request commands for that peer** were observed, at **records #561 and #578**, both earlier in the capture.
- Both requests received successful HCI Command Status `0x00` for opcode `0x0419` (records **#566 and #580**). **Command Status success indicates acceptance, NOT completion of the remote name inquiry.**
- Across the entire 1,789-record capture, **zero HCI Remote Name Request Complete events (event code `0x07`) match the DS3 peer's address**. Other devices produced these events; e.g. #588 is a successful Remote Name Complete **for another peer**, not DS3.
- There is no proof that every PIN request caused an additional name request. The two DS3 name requests predate all four authentication attempts, and subsequent attempts may have cached/pending internal name state. Missing name-complete is a **specific hypothesis** linking observed HCI and the original ELF deferred-name branch, not a proven causal trace.

**Significance:** The combination of (1) BTA PIN handoff deferring when name is absent and (2) the exact DS3 peer having name requests accepted by controller with no matching completion makes the **remote-name resolution callback** a materially stronger suspect than an abstract Java pairing UI failure. Next source/binary target is the deferred name-request call at `0x137438 → 0x24b804`, its eventual completion callback, and interactions with BTA pairing state. A testable safe design might use a scoped known-name fallback for USB-enrolled DS3, **only if** callback path and recovery safety are later proven; do not implement or inject now.
