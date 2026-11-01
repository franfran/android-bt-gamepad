# M3 DS3 — S7 plugin to S8 security integration contract (offline feasibility)

## Decision, 2026-10-31

**A native plugin can carry decision code, but cannot solve DS3 by merely being loaded.** The S7 loader and S8 security interception are independent problems, and the OEM Java HID Host check is a third constraint. No supported policy callback, live loader, or two-gate implementation has yet been demonstrated. The next review should focus on a callable policy interception mechanism, **not** redoing remote `dlopen` experiments or another PIN guess.

## Precise evidence in existing repo

1. `docs/S7-C4C-HANDOVER.md`, `docs/SAFETY.md`, PRs #3–#5: independently started test process, 48 workers, remote `dlopen`, ARM32 SVC/trampoline and fault quarantine **PASS on M3 only for a test-owned process**. Current Bluetooth process loader remains C4C-3 **NO_GO**.
2. PR #32 + #38: original M3 `libbluetooth.so`, fingerprint `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`: incoming CLOSED/event 10 Classic L2CAP route retains remote BD_ADDR and service PSM at `l2c_csm_execute` before `btm_sec_l2cap_access_req` callsite VMA `0x2897b4`. **Address is an ELF VMA, not a usable runtime patch location**.
3. PRs #39–#40: later per-device BTM authentication procedure may initiate HCI `0x0411`; HCI failure `0x22` does not identify whether the root problem is host Bluetooth firmware, PS3 legacy behavior or policy.
4. Verified owner original `Bluetooth.apk` SHA256 `d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f`: JNI-connected-state callback issues handler message 3; initial connected state invokes `okToConnect` requiring `BOND_BONDED`; rejection calls `virtualUnPlugNative`. **A native-only hook cannot suppress this later Java rejection.**

## Required interface between components (DESIGN, not an exposed OEM API)

```text
UsbEnrollment:
  id: controller fingerprint from physically attached owner DS3
  paired_host: exact local M3 adapter
  approved: explicit one-time owner enrollment
  revoked: false
  validity: owner-managed
  proof_note: MAC/USB VID:PID by themselves are spoofable, not cryptographic authentication

NativeCandidate:
  peer_identity
  adapter_identity
  incoming: bool
  transport: BR_EDR
  service_psm: 0x11 | 0x13
  profile: HID_HOST
  session_nonce: process-local / ephemeral
  original_security_requirement: unchanged for all unmatched requests

JavaCandidate:
  peer_identity
  connected_state_transition
  enrollment_session (if safe interface exists)
  original_bond_state
  original_connection_policy

Decision:
  DENY | UNCHANGED_ORIGINAL_SECURITY | REVIEWABLE_CABLE_CANDIDATE
  (No result from this offline contract is a real Bluetooth authentication success.)
```

**Policy invariants:** default to exact original behavior for all unknown/unapproved devices, non-HID PSM, outbound/LE traffic, revoked enrollment, changed adapter, expired/duplicate session and failure. Never rewrite global security mask `0x36`, spoof bond state, create fictitious LinkKeys, or treat the device name alone as authorized identity. Any software-only allowlist has residual address-spoof / rogue-HID-input risks; review whether sufficient for an owner-controlled local setup.

## Mechanism feasibility matrix

| Route | Calls per-device native decision before auth? | Handles Java HID bond check? | Deployability |
|---|---|---|---|
| Existing exported OEM callback/plugin | **Not found/proven** | Separate Java provision needed | Investigate exact OEM ELF/API evidence only |
| S7 `dlopen` inert addon | **No: maps a library, no interception** | **No** | Real BT service unsafe/unproven under C4C-3 |
| Native function detour/inline hook in service | Could, in theory, wrap caller with peer+PSM | No; requires Java/HID path solution | High-risk runtime text patch + concurrency + rollback; **NO_GO** |
| JNI Java-only pairing helper | No, since pre-auth L2CAP precedes Java connected-state | May control some UI flow; cannot assume bond success | PIN-only **NO_GO** |
| Reproducible offline OEM-stack rebuild/patch | Can implement scoped policy at source-mapped caller | Can implement second gate | Requires signed/system replacement, AVB/recovery evaluation; **design only** |

**Key possible simplification:** a genuine standard Android `BOND_BONDED` outcome would satisfy Java gate without patching HID Host; however BlueZ cable pairing explicitly targets nonbonded Sixaxis and no working M3 bond has been observed. Do not prematurely declare a Java patch *unconditionally* necessary. Conversely, if nonbonded cable admission is chosen, a viable Java-policy integration **is necessary**.

## Exact next decision gates

A. Check **supported** native callback existence in the actual OEM stack; a symbol/callback must be registered and invoked at the right ingress, not just exported. If none is evidenced, label it **UNVERIFIED/NO DOCUMENTED API**, not absolute absence.

B. Derive the minimally invasive observation strategy, reusing existing passive sanitized HCI captures, to distinguish *security rejection* from *controller LMP timeout* (0x22). Static callgraphs alone cannot establish controller compatibility or policy-fix efficacy.

C. For a source-level two-gate candidate, run offline negative tests against non-enrolled HID, keyboards, wrong transport and PSM, revoked/controller mismatch, host mismatch, and dual-channel ordering. Do not simulate success by asserting a mocked 'authenticated' bit.

D. Validate independent rescue path and owner-approved recovery checklist before any genuine service loader trial. Current state **NO_GO**, no automatic restart/retry. Staged file cleanup is **not** code unload.

## Operational discipline

- Already **PASS**: physical USB DS3 controls Android/RetroArch, sixpair sets M3 host address.
- Final **PASS** (not yet achieved): unplug, press PS, native BT connection, legitimate HID InputDevice, wireless RetroArch menus/buttons, repeated reconnect and reboot.
- No firmware flash (2025 update lacks fix), no sidecar BlueZ host, no external dongle.
- Keep PR #50 draft; do not merge, install, flash, inject or modify Bluetooth security without separate Owner approval.
