# S8 — Offline Bluetooth HID authentication trace regression

**Scope:** Analyze an existing **private local** M3 Bluetooth snoop, without contacting M3, changing Bluetooth, loading add-ons, modifying pairing state or exposing PINs / Link Keys / device addresses.

## Purpose and what is already known

The archived device investigation in `research/retrobox-stage3c-gate2-l2cap-auth-addendum.md` and `research/retrobox-stage3c-gate2-hci-evidence.md` established:

- HCI record #144: DS3 HID Control L2CAP connection request (PSM 0x11).
- #151: host `Authentication Requested` (ACL handle 0x0080).
- #153/#154: Link Key Request / Negative Reply.
- #156/#157: PIN Code Request / host PIN Reply command.
- #159: `Authentication Complete` status **0x22** (LMP Response Timeout), then #161 disconnect with reason 0x22.
- The second historical attempt timed out again; a PIN reply command was not observed.

This is **already established research** and must not be rediscovered via generic USB or JNI mapping loops. The new tool is an *offline regression reader* for the privately retained original btsnoop (if still available) and future independently approved captures. Current repo intentionally excludes original raw btsnoop because of secret-bearing data.

## Usage (only if a local original is already retained)

```sh
python3 experiments/s8-bt-auth/offline_auth_trace.py /private/local/path/m3-ds3-btsnoop.log
```

The parser accepts bounded btsnoop v1 / H4 DLT 1002, identifies HID Control connection attempts on PSM `0x11`, relates the handle to HCI Authentication Requested/Authentication Complete and disconnection, and correlates Link Key/PIN events only where a single active attempt and address matching permit. It reports **only** sanitized attempt chronology, statuses and source record indices; never prints raw addresses, PIN values, keys, HCI payload or the input path. Output always retains `decision=NO_GO` and `injection_authorized=false`.

Synthetic regression tests cover the historical sequence, second attempt with no PIN reply, different controller address, wrong handle, incomplete capture and privacy. **Tests cannot substitute for an owner original packet trace** or establish the actual internal native function callsite.

## Critical source/ABI observation

M3 machine-code research indicates HID PSM `0x11` and `0x13` share security registration mask `0x36`. Android 12 reference `btm_sec_l2cap_access_req(..., psm, ...)` knows the PSM, whereas `btm_sec_l2cap_access_req_by_requirement(..., security_required, ...)` does **not** include PSM in its parameter list. An imagined per-PSM security override at the latter interface is therefore insufficient without context propagation or a higher-level decision point. The M3 exact runtime branch, callsite and firmware behavior remain UNVERIFIED.

- Android 12 source reference: https://android.googlesource.com/platform/system/bt/+/refs/heads/android12L-d2-s8-release/stack/btm/btm_sec.h
- Previous M3 offline binary audit: `research/retrobox-stage3c-gate2-security-decision-audit.md`
- BlueZ cable-paired incoming HID discussion is a design comparison, not directly portable Android code: https://www.spinics.net/lists/linux-bluetooth/msg119483.html

## Decision boundaries

1. HCI command `PIN Code Request Reply` appearing is evidence of host submission, **not** peer reception, successful authentication or correct PIN.
2. `0x22` means the controller reported LMP response timeout. This does **not** uniquely identify the faulty side, security-policy branch or a safe patch.
3. Even HCI authentication status 0 cannot by itself prove HID channel completion, Android InputDevice registration or RetroArch success.
4. No globally changed mask `0x36`, LinkKey fabrication, guessed PIN, unverified callback patch, Bluetooth restart or service injection.
5. Next research deliverable is a **source-level pairing security callsite contract** and an isolated test, not a live M3 Bluetooth experiment. C4C-3 NO-GO remains binding.

## Limitations

The decoder does not guarantee complete multi-controller disambiguation if the capture lacks connection-complete/address context; unknown or ambiguous identity should not be treated as proof. It does not reconstruct fragmented L2CAP packets. A missing sequence can mean a partial capture. It is intentionally not a general-purpose Bluetooth analyzer.
