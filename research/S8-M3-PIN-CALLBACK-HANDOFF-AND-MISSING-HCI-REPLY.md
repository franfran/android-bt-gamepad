# S8 — Real PIN request callback handoff: why M3 can receive PIN request but send no reply

**2026-10-29, offline research only.** Exact original owner-uploaded M3 Android 12 ARM32 `libbluetooth.so` SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`, inspected using mini-debug symbols plus original Thumb instructions. Original ELF VMAs below; **llvm-objdump's spurious global AVRCP symbol labels must not be used**. No original ELF/secret Bluetooth data committed.

## Important: supersedes earlier inaccurate PIN assertion

**Owner's now-available raw HCI btsnoop** `btsnoop_hci(1).log` shows four authentication attempts receiving HCI PIN Code Request, **ZERO** host PIN Code Request Reply (opcode `0x040D`) **and ZERO** host PIN Code Request Negative Reply (`0x040E`). Each Authentication Complete returns status `0x22` ~30.06 seconds after PIN Request. The earlier conclusion that a six-byte PIN Reply had been sent was **wrong**: six-byte address fields in request events are not PIN responses. The rotated `.last` log does not contain the same failure. Root cause is not yet proven; missing host response is the **highest-priority evidence**.

## Original machine code: request dispatch and user-callback handoff

Mini-debug symbol `btm_sec_pin_code_request(uint8_t*)` at **0x25d7a0**, size 896. The original M3 instructions demonstrate **three mutually exclusive possibilities** rather than an unconditional immediate HCI reply:

1. `0x25d99a` loads stored PIN length from security global byte `+0x3661`. If nonzero, `0x25d9c0` loads PIN bytes at `+0x3662`, invokes **`btsnd_hcic_pin_code_req_reply` at 0x25d9c8 → 0x27c87c**, then clears the saved PIN length at `0x25d9d2`. **This path is not observed in the four captured attempts.**
2. Some policy/state branches call **`btsnd_hcic_pin_code_neg_reply` at 0x25d902 → 0x27c922**. This command is **also absent** in four attempts.
3. If no stored PIN, the function at **0x25d9ea** fetches the **global callback pointer from `+0x3620`** and another global state byte `+0x365d`. `0x25d9f6` diverts to a negative-reply branch if state suppresses callback; `0x25d9f8` diverts if the callback pointer is NULL. When eligible, `0x25da10..0x25da3e` stores remote address and device context into security globals, and later the callback dispatch proceeds at `0x25daa8..0x25dad2`: `ldr.w r12,[r7,#0x3620]` then **`blx r12` at 0x25dad2**, with address in r0 and event/context args in r1/r2/r3. Exact semantics of each callback argument require deeper mapping.
4. The registered callback is *asynchronous*. Code reaching `blx r12` does not itself issue HCI opcode `0x040D`; the upper layer must drive a separate reply API.

## Original machine code: reply API separate from request callback

Mini-debug symbol **`BTM_PINCodeReply(RawAddress const&, unsigned char, unsigned char, unsigned char*)` at 0x256a20**.

- `0x256a76` checks pairing state `+0x3672 == 3`; `0x256a80..0x256a88` compares the supplied remote address to stored pending address `+0x3674`. Wrong pairing state/address can divert the response.
- `0x256ad4..0x256ae2` validates PIN length <=16 and success/argument conditions, with different non-success handling.
- The actual positive HCI response tail-calls **`btsnd_hcic_pin_code_req_reply` at 0x256b3a → 0x27c87c**; negative path tail-calls **`btsnd_hcic_pin_code_neg_reply` at 0x256b86 → 0x27c922**.

This provides a strong *mechanistic explanation* for why a controller can emit PIN Code Request while the host never responds: the native layer can defer to its registered callback, and a missing/unhandled/failed upper-layer response can leave the controller waiting. However, **the private HCI trace alone cannot distinguish callback not registered, callback not invoked, upper layer not handling it, or `BTM_PINCodeReply` called with rejected state/address/arguments**. Claims that a particular Java class is responsible would be premature without btsnoop-correlated platform logs.

## Focused research/diagnostic evidence without M3 modification

Preferred next evidence: existing `logcat`/dump logs at the same pairing time, checking high-level Bluetooth pairing request events and callbacks (e.g. `BTA_DM_PIN_REQ_EVT`, `pin_req_cback`, `BTM_PINCodeReply`, `BondStateMachine`) **without publishing PIN or MAC**. Correlate timestamps to precise PIN Request events in HCI. Relevant source-level mapping of M3's bundled Fluoride interfaces (BTA/BTIF) can then tell whether a callback was registered and whether reply was attempted but rejected.

Do **not** immediately inject a synthetic PIN Reply, assume address-only device identity proves trust, bypass global HID PSM mask `0x36`, replace system `.so`, restart Bluetooth service or run privileged hook. Any proposed DS3-only compatibility fix would need a trusted cable-enrollment gate, explicit owner approval, isolation from other Bluetooth peers, and proven recovery; S7 C4C-3 live injection gate **NO_GO** remains.

## Bottom line

**What is proven:** Four incoming PIN challenges never receive HCI PIN reply (positive or negative). Native M3 pairing API has a real asynchronous callback path and separate state-checked `BTM_PINCodeReply` response. The unreturned PIN is a *host-visible gap*, materially more actionable than speculative LMP incompatibility or PIN byte order.

**What is NOT proven:** which exact callback condition failed on M3, whether Android displayed a pairing request, whether upper-layer code tried a response, and the true controller/DS3 LMP failure cause.
