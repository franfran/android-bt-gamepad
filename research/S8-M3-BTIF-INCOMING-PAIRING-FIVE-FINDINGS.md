# S8 — Five findings on incoming DS3 PIN event and BTIF pairing policy

**Research:** owner M3 original SHA verified `libbluetooth.so` (ARM32 mini-debug), owner's genuine 1,789-record btsnoop, plus explicitly **reference-only** AOSP Android 13 `btif_dm.cc` (vendor M3 is Android 12; exact source parity NOT established). This is a static source cross-check, not a live test. Date 2026-10-29.

## Finding 1 — AOSP automatic PIN path is *local-initiation gated*

In AOSP `btif_dm_pin_req_evt`, there is an explicit `pairing_cb.is_local_initiated && !p_pin_req->min_16_digit` condition before automatic PIN fallback for selected legacy Class-of-Device categories. Separately, AOSP `btif_dm_cb_create_bond` sets `pairing_cb.is_local_initiated=true` when local host initiates bonding. The four observed DS3 attempts start with DS3 initiating peer HID PSM 0x11, so it is reasonable to **hypothesize** the local-initiation predicate is false; nevertheless PSM originator and bond originator are different concepts, and **actual M3 pairing_cb.is_local_initiated is NOT captured**.

**Consequence:** If M3 matches the analogous AOSP policy and local initiation was false, it would **not** auto-generate a PIN: instead `invoke_pin_request_cb` must notify platform UI/policy. Importantly, Android's built-in legacy auto-PIN is often ASCII `0000` for selected devices, **not** DS3's host-address PIN; enabling this fallback globally would be invalid for DS3.

## Finding 2 — BTIF can drop a competing PIN event silently at HCI level

In AOSP, `btif_dm_pin_req_evt` checks `pairing_cb.state == BONDING && bd_addr != pairing_cb.bd_addr` and **returns without HCI PIN positive/negative reply** if bonding some other peer. Owner HCI log contains substantial traffic from other Bluetooth peers, though **that does not prove a competing bond** at any of the four PIN request timestamps. This is a second plausible mechanism for zero HCI replies that does not require name-resolution stalls. Need same-time platform logs / pairing state to test.

## Finding 3 — M3 ELF has real user-facing PIN request callback plumbing, not just a theoretical AOSP route

Original M3 ELF mini-debug exports:
- `btif_dm_upstreams_evt(uint16_t,char*)` **0x1cbfe4**, source-level AOSP event router for `BTA_DM_PIN_REQ_EVT`;
- `invoke_pin_request_cb(RawAddress,bt_bdname_t,unsigned int,bool)` **0x1a9514**, size 144, indicating M3 includes the callback invocation layer;
- `btif_dm_pin_reply(...)` **0x1cf1a4**, whose existing original-ELF branch and BTA queuing path were traced in PR #44;
- `BTA_DmPinReply` **0x138ce4**; native `BTM_PINCodeReply` **0x256a20**, whose pending-state, peer-address and PIN-length guards were traced in PR #43.

Original disassembly of M3 `invoke_pin_request_cb` at **0x1a953c..0x1a9574** allocates a closure/task object and enqueues asynchronous callback handling via `0x1c9fb0`, rather than directly constructing an HCI command. This agrees with the reference AOSP `btif_dm_pin_req_evt` default call to `invoke_pin_request_cb(...)`. It **does not yet prove the four actual DS3 events arrived at this function**. Next step is mapping the callback's runtime ingress and Java handling, not reinvestigating HCI opcode senders.

## Finding 4 — Remote name is not the only gate; software error-completion is verified

The previous original ELF PR #45/#46 analysis confirmed a missing-name request `BTM_ReadRemoteDeviceName` may defer BTA PIN notification, **but** request-start failure causes immediate BTA PIN fallback and timeout can call completion with `0x1f`. Owner HCI capture showed two DS3 Remote Name Request commands accepted, but no DS3 Remote Name Complete; these happened *before* the four PIN requests, and cannot prove PIN was blocked while waiting for name during each attempt. Treat name-resolution stall as an **unconfirmed alternative**, not established root cause.

## Finding 5 — True branch discriminator requires BTIF/Java pairing evidence, not another binary callsite

Owner's genuine HCI log: four incoming PIN requests, zero PIN Reply `0x040d` and zero PIN Negative Reply `0x040e`, about 30.06s to `0x22` failure each. This establishes an observable **host-side missing response**, but HCI contains no JNI/Java callbacks or BTIF global pairing state. Under reference AOSP, if `invoke_pin_request_cb` runs, it notifies platform callbacks; `btif_dm_pin_reply` is a separate upper-layer reply API. In M3, callbacks are asynchronously enqueued. Therefore the next practical differentiators are **presence/absence of `ACTION_PAIRING_REQUEST` and `BluetoothDevice.PAIRING_VARIANT_PIN` in existing logcat** or other platform logs, plus BTIF `BTA_DM_PIN_REQ_EVT`, `BondStateMachine`, bond state/peer conflicts. Logs might not exist; if unavailable, do not claim a diagnosis.

## Evidence ranking

| Candidate | Evidence | Confidence |
|---|---|---|
| Host never emitted PIN response | 4 real HCI sequences, 0 positive/negative PIN commands | **Observed** |
| PIN prompt/user callback needed for incoming pairing | AOSP local-initiation gate + M3 native callback symbol and closure plumbing | **Strong hypothesis**, actual local flag unknown |
| Silent suppression because another device bonding | Explicit AOSP early-return gate | **Alternative, runtime unverified** |
| Remote name callback stuck | Name requests without matching HCI complete; BTM software timeout/fallback exists | **Weakened hypothesis** |
| M3 controller/DS3 incompatible even with valid PIN | No valid PIN exchange observed | **Not established** |

## References

Android 13 AOSP branch `btif_dm.cc` as **reference**:
https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/heads/android13-security-release/system/btif/src/btif_dm.cc
Relevant `btif_dm_pin_req_evt` near lines 757–835; `btif_dm_cb_create_bond` 671–714; `btif_dm_pin_reply` near 2162–2176.

## Decision and next work

Prioritize **offline inspection of existing logcat from same pairing window**, if any. If none, a separately owner-authorized read-only collection of platform pairing state could discriminate without modifying Bluetooth code; existing btsnoop alone cannot. A proposed DS3-only solution must be scoped to owner USB enrollment and reviewed for spoof resistance, rollback, timer and controller compatibility; **do not** auto-reply to arbitrary MACs, relax HID `0x36`, inject or patch the M3. **S7 C4C-3 NO_GO**.
