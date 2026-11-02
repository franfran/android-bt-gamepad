# I2/I6 — UHID Candidate Lifecycle v2: Atomic Write + Quarantine

**Workstream:** Draft PR #52 (`research/m3-ds3-compat-adapter`). **Pinned reference:** `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. **Status:** offline prototype / device NO_GO.

## 1. Why v1 is superseded

The previous `h618_uhid_candidate_fence_disabled.patch` and `candidate_uhid_fence.h` are archived v1 research evidence, **not a safe drop-in candidate authorization gate**. A separate `AllowKernelEvent(fd)` check unlocked **before** actual `write(/dev/uhid)`, introducing a potential check-then-write race. Calling `Revoke(ticket)` removed the fd from the block table while it might still be open, so later UHID_INPUT could fall through the ordinary path. No actual M3 exposure was established because these research macros were never enabled.

**Do not apply v1 and v2 together.** v2 is a standalone replacement diff against pristine pinned H618, and it uses a different, unset research macro.

## 2. New code / pinned H618 source patch

- `experiments/m3-ds3-cable-session/candidate_lifecycle_gate.h`: fixed-capacity 8-slot deny-only `CandidateLifecycleGate`. No candidate authentication, Java approval, LinkKey, bond or HID-grant operation.
- `experiments/m3-ds3-cable-session/test_candidate_lifecycle_gate.cc`: 76 assertions checking normal HID unchanged, registered candidate CREATE/INPUT denied, DESTROY allowed, exact-ticket stale cleanup, double quarantine, failed close retention, slot exhaustion, reuse, and concurrent writer/register serialization.
- `experiments/m3-ds3-cable-session/h618_uhid_lifecycle_v2_disabled.patch`: adds a conditional header and entry points to `system/bt/btif/co/bta_hh_co.cc`, while preserving existing code when `RETROBOX_DS3_UHID_LIFECYCLE_V2_RESEARCH` is OFF. Also creates `system/bt/btif/co/retrobox_candidate_lifecycle_gate.h` with exact host header bytes.
- `experiments/m3-ds3-cable-session/verify_h618_uhid_lifecycle_v2.py`: verifies patch guard/header shape and runs strict G++ host test twice (normal and ASan+UBSan), with optional `--source-tree` checking `git apply --check` against **exact** pinned HEAD; no patch applied.

### How the v2 gate works

`RegisterCandidate(fd,handle,epoch,requestId)` must be called by a **future trusted Native classifier, before any UHID write**. It only registers an unapproved candidate. `WithKernelWrite(fd,event,actual_write)` holds one mutex over **both the decision and `actual_write` callback**; pending or quarantined candidates cannot issue `UHID_CREATE` or `UHID_INPUT`. UHID_DESTROY and unrelated messages remain eligible for the original write path.

`Quarantine(exact_ticket)` records disconnect/Java veto without unblocking fd. `CloseQuarantined(exact_ticket, close_fd)` requires a matching ticket and successful real close **within the same lock** before removing the block; failed close or stale ticket leaves the candidate blocked. The early guard in `bta_hh_co_send_hid_info` is only an optimization to avoid stock error handling closing fd as if the descriptor were corrupt; the **final** `uhid_write` guard is the authority.

### Important integration boundaries

- **NO Native candidate registration caller exists yet.** v2 starts with an empty table. Turning on this macro alone cannot identify DS3, and an unclassified candidate may still follow the stock path. This is therefore **not a complete pre-UHID security enforcement**.
- On failed registration (including exhausted table), future caller must **abort and close the candidate connection**; falling through to ordinary HID would nullify the intended safety gate. Current patch has no such caller or proof.
- A USB F2/F5-derived MAC match is only `kAddressCandidateNotAuthenticated`, not secure identity. Neither the BlueZ-inspired enrollment model nor Java `kCableReviewOnly` can authorize BTM, bonding or UHID.
- **Thread ordering remains unproven on Android.** Holding mutex through an actual `write` reduces the demonstrated TOCTOU window but may introduce latency or lock-order inversion if called from reentrant callbacks; the real H618/Android build and live interleavings have not been tested.
- `CloseQuarantined` has no source caller: existing `bta_hh_co_destroy`/descriptor-error branches still call `close` directly. A proper integration must centralize fd ownership and ensure no double-close, fd reuse before new registration, or stale close of a successor.
- On an OS close error, retaining the tombstone is fail-closed but may block a reused descriptor; a production design needs exact OS fd-generation/lifetime accounting, not only numeric fd/handle.
- The v2 research patch remains disabled-by-default. It is **not** a real DS3 Bluetooth fix; HCI legacy authentication timeout `0x22` is still upstream and unresolved, with full matching M3 Android BSP build NO_GO.

## 3. Evidence and limits

Local isolated Debian GCC 14.2.0 compiled the **exact new GitHub blob bytes** for `candidate_lifecycle_gate.h` and `test_candidate_lifecycle_gate.cc` (Git blob hashes: `c314ace842d9312a36d204636fa549531eba80b4`, `c4118c00f6793cdf96065b14253a49d5ef11bfe2`). Results:

```text
g++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread test_candidate_lifecycle_gate.cc -o test_gate
./test_gate
76/76 PASS (candidate lifecycle quarantine + atomic writer host)

g++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread -fsanitize=address,undefined -fno-omit-frame-pointer test_candidate_lifecycle_gate.cc -o test_gate_san
ASAN_OPTIONS=detect_leaks=1 ./test_gate_san
76/76 PASS (candidate lifecycle quarantine + atomic writer host)
```

All **four modified-file hunks** were checked line-by-line against the exact pinned H618 source, with source/new counts and offsets. The new header matched the committed source byte-for-byte. The exact committed Python verification script, a full-tree `git apply --check`, Soong/Java/ARM32 target build, and actual M3 Bluetooth operation were **not** executed. 76 represents assertions in one test executable, not 76 independent test suites.

## 4. Decision / next milestone

**Offline v2 lifecycle model PASS. Production Native classification/registration-before-first-write, candidate abort-on-registration-failure, fd ownership and Native/Java session-bound admission NOT IMPLEMENTED; target deployment NO_GO.**

Next useful work: design a **source-bound classification-before-UHID-open** seam in the BTA/BTIF call path, and an explicit abort-on-registry-failure policy. Before hardware: run full BSP patch/build checks and normal bonded HID regressions, then separately review security scope and independent recovery with the Owner. PR #50 research archive and PR #51 build/source workstream remain independent; keep PR #52 Draft.
