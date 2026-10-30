# S8 — Name resolution fallback: correcting the PIN callback stall hypothesis

**2026-10-29; offline original M3 ELF review.** SHA256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`. No M3 operations. This work extends and **qualifies** Draft PR #44. ELF VMAs in Thumb mode, original mini-debug names (not objdump's erroneous global AVRCP labels).

## Actual resolved callee + callback identity (new)

The previously unknown `0x137438: bl 0x24b804` resolves from mini-debug to:

**`BTM_ReadRemoteDeviceName(RawAddress const&, void (*)(void*), uint8_t)`** at code `0x24b804` (symbol value `0x24b805`, size 380).

The PC-relative callback argument is specifically **`bta_dm_pinname_cback(void*)`**:
- At `0x13742e` BTA loads literal `0x137478`, little-endian word `0x000009cf` to `r1`.
- At `0x137436` `add r1,pc` resolves to Thumb function pointer `0x137e09`, code `0x137e08`.
- `0x137438` calls `BTM_ReadRemoteDeviceName` with that callback and `r2=1`.
- This callback address agrees with mini-debug symbol `bta_dm_pinname_cback(void*)` at 0x137e09, size 240.

This completes a concrete missing link between the asynchronous missing-name PIN path and its intended callback.

## Critical correction: when starting a name request fails, it falls back to PIN event

The branch at `0x13743c: cmp r0,#1`, `0x13743e: bne 0x137456` checks the name-request API result:

- If `BTM_ReadRemoteDeviceName` returns **1** (started), `bta_dm_pin_cback` returns with the deferred PIN context preserved; it waits for `bta_dm_pinname_cback`.
- If return value is **not 1**, code at **`0x137456..0x13746e` ends by branching to `0x1373ce`** (direct immediate PIN event dispatch), rather than silently dropping the request.

Therefore our earlier hypothesis that an absent Remote Name Complete **alone necessarily prevents** PIN dispatch is **too broad**. To blame a name wait, the DS3 PIN request must actually have entered BTA's missing-name branch, have received `BTM_ReadRemoteDeviceName == 1`, and have failed to invoke the subsequent completion callback before the 30-second HCI timeout. This specific condition remains UNVERIFIED.

## What the completion callback actually does

The exact original `bta_dm_pinname_cback(void*)` function at **0x137e08** shows:

- Reconstructs and reads pending peer context from global `+0x1a0..+0x1b4`.
- At `0x137e2c..0x137e50`, branches based on pending event state byte `+0x1a9` (compares to `0x0a`).
- At `0x137e52..0x137e80` checks the name-completion result and copies available name bytes (capped) into a BTA callback event; at `0x137e64..0x137e6a` constructs an empty-name event on a separate path.
- At `0x137ed2`, loads BTA security callback from `+0xb0`, `0x137ed6: cmp r2,#0`, and **`0x137edc: blxne r2`**: invokes registered callback with pending event and context when present.

The completion code is not simply `if remote name failure then abort`; it includes a **no-name fallback** to a BTA event. Whether a completion callback happened for this DS3 peer is not established by HCI alone; no matching HCI Remote Name Complete is visible in the uploaded main capture.

## Lower-level request semantics (original ELF)

`BTM_ReadRemoteDeviceName` at `0x24b804` has transport/status branches and a busy guard: at `0x24b8c8..0x24b8d2`, nonzero global `+0x296` can return value **2** without starting another request. `0x24b8d8` retains callback pointer in global `+0x278`, then Classic path at `0x24b928..0x24b948` prepares HCI command and sets `+0x296=1` for started request. Error/unsupported modes return other statuses.

Implication: If another Bluetooth remote-name query occupies the stack, **BTM_ReadRemoteDeviceName will not always report started**. Crucially, BTA's non-1 fallback means being busy is not automatically a PIN stall.

## Evidence from real DS3 btsnoop and what it does not prove

The actual owner-uploaded 1,789-record HCI log contains DS3 Remote Name Requests at #561 and #578; each got successful controller Command Status but no matching Remote Name Complete for the DS3 address. They occurred **before** the four PIN Code Request events (#595/#638/#1655/#1755), and the capture has no corresponding HCI PIN replies (positive or negative). A matched Remote Name Request absence *at the PIN timestamp* makes it especially important **not to assume** that BTA was waiting for a new name lookup during each pairing attempt.

The HCI log cannot show the BTA callback state, name-cache availability, internal HCI request queuing, or whether PIN Reply was attempted via Java and rejected in BTM. The static code supports multiple possibilities.

## Further discriminator and safe next tasks

1. Establish whether a DS3 PIN event was queued to the asynchronous name callback **during** an authentication attempt using existing device platform logs (if available); compare against HCI packet timestamps, not just presence/absence across the whole file.
2. Reconstruct BTM remote-name request completion/timeout processing and determine if it invokes `bta_dm_pinname_cback` on error/timeout; its likely entry symbols include `btm_process_remote_name` at 0x24c5f8 and `btm_inq_remote_name_timer_timeout` at 0x24c7d8. A callback guaranteed on timeout could further weaken the stuck-name theory.
3. Trace BTA `BTA_DM_PIN_REQ_EVT=2` receipt into BTIF, and determine whether any DS3-specific PIN policy existed. Do not conclude firmware fault or automatically inject a PIN.

**Safety:** No `.so` replacement, injection, Bluetooth restart, root process edit, or global HID mask 0x36 change. Original wired DS3 baseline remains settled. S7 C4C-3 gate: **NO_GO**.

**Conclusion:** We resolved the previously anonymous remote-name call and its exact callback and showed that a failed *start* triggers direct PIN-event fallback, while the completion callback can report an empty name. The simple 'no HCI Remote Name Complete → PIN request is indefinitely blocked' explanation is **not proven**; future work must isolate a real callback wait or a separate BTIF/Java policy gap.
