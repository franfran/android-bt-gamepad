# M3 DS3 Legacy PIN — Implementation Architecture and Validation Gates

**Status:** planning-only Draft PR. **Target:** iMETBOX M3 International, Android 12 API 31, Allwinner H618, built-in Bluetooth. **No device modifications authorized.**

## Source of truth and Git topology warning

- Owner handoff: PR #49 (merged **into PR #48's research branch**, not demonstrably incorporated into `main`); review its patch and owner decision before implementation.
- PR #48 remains a stacked Draft research PR. Issue #6 documents the independent Bluetooth injection NO_GO.
- `main` currently does **not** contain `docs/M3-DS3-PAIRING-ROOT-CAUSE-AND-OEM.md`; preserve PR #49's findings and arrange a separately reviewed forward-port to main rather than assuming it landed there.
- Do not repeat USB input functionality testing or broad native reverse engineering.

## Established diagnosis (conditional)

Actual OEM `TvSettings.apk`: `BluetoothPairingRequest.onReceive()` calls `onPair(variant, null)`; PIN variant 0 invokes `BluetoothDevice.setPin(String)` with null, rejected by actual M3 framework. Actual `Bluetooth.apk` selects variant 0 for non-keyboard and `min16Digits=false`, variant 7 for true. Historical HCI PIN requests had no PIN replies and timed out, but **runtime min16Digits/variant for those attempts was not directly observed**. Installed 2024 vs International 2025 Java comparisons: TvSettings.apk and Bluetooth.apk identical; relevant framework PIN behavior unchanged. Owner decided against firmware flash for this issue.

## Candidate architecture — preferred if Android permission / delivery gates pass

```text
Existing USB enrollment (owner authorized, local-only)
   -> validate real DS3 identity, current host adapter address,
      controller's programmed master, and explicit allowlist
   -> one-shot arming (never blanket enrollment)
   -> privileged Android receiver / helper, exact DS3 request + variant check
   -> exact **binary** legacy PIN byte[] through supported/verified platform API
   -> result + bond / HCI success monitored and sanitized
   -> disarm, no background retries
```

**IMPORTANT:** DS3 legacy PIN may be six **raw** bytes representing the Bluetooth host adapter BD_ADDR, with controller/host byte-order expectations to be independently established from known successful pairing or documented protocol. It is not ASCII `0000`, not a text representation of a MAC, and not safely convertible through `setPin(String)`. Verify byte order, raw-byte API access, valid length (6), and an offline golden-vector test before any real request. Never commit the host/controller MAC, PIN, LinkKey, bond DB or raw HCI log.

### Options and recommendation

| Route | Pros | Blockers / risk | Gate |
| --- | --- | --- | --- |
| Standalone privileged helper + tightly scoped pairing receiver | Avoids rewriting proprietary OEM APK and native injection; potentially clean uninstall / disable | `BLUETOOTH_PRIVILEGED` is protected, likely requires system-app placement and appropriate allowlist/signing; hidden `setPin(byte[])` API may be inaccessible; competing OEM receiver; routing may be nonexclusive | **Preferred for offline prototype only**, pending verified manifest, permission, API and broadcast semantics |
| Supported system integration / OEM Settings hook | Correctly owns pairing UX; no competing receiver if supported extension exists | No documented extension presently shown on M3; need verify vendor package exposes one | Explore offline manifest/resources; prefer if real supported hook exists |
| Adjust OEM TvSettings APK receiver | Fixes root handler directly; deterministic event ownership | APK signing/privapp placement, OTA integrity, system partition/AVB, rollback and possible boot risk | **Fallback only** after helper ruled out and separate Owner approval |
| Root-only shell companion / generic third-party APK | Easy to prototype without system image | Shell UID/root does not automatically confer Android framework signature permissions or safe binder context; race against OEM receiver | **NO_GO** absent proven supported API/permission path |
| Native Bluetooth process injection / HCI direct response | Low-layer control | C4C-3 NO_GO, service safety, auth state corruption | **NO_GO** |

**Broadcast ownership must be measured, not assumed:** determine whether `ACTION_PAIRING_REQUEST` is ordered / protected in this build, priority interaction with `com.android.tv.settings`, whether OEM receiver acts first, and whether aborting or racing would be necessary. A second receiver that races `setPin` is **not acceptable**. If there is no safe, deterministic integration, mark privileged helper NO_GO and escalate to a reviewed OEM receiver patch design.

### Trust and PIN source contract

1. Enrollment allowed only while owner explicitly arms a single controller, using existing physical USB enrollment record; do **not** infer trust from DS3 display name, CoD, or MAC prefix alone.
2. Locally verify USB VID:PID `054c:0268` **and** independently associate the physically attached controller's Bluetooth device address and programmed master BD_ADDR; USB VID:PID identifies a product class, not an individual trusted controller. If pairing attempt cannot be bound to precisely that enrolled controller, fail closed.
3. Query current built-in adapter BD_ADDR through an explicitly validated privileged platform mechanism; compare with the already enrolled master, refuse changed/unknown address. Never silently rewrite controller master or fabricate LinkKeys.
4. PIN source should be the validated host BD_ADDR as exact six raw bytes only after evidence confirms this DS3 handshake's byte order. Reject zero length, ASCII MAC, unverified mapping, or wrong pairing variant.
5. One pending request, one known DS3, bounded expiry, explicit one-shot disarm, no general-purpose pairing receiver for untrusted devices. Leave unrelated Bluetooth devices to OEM behavior.
6. Store allowlist locally with minimum permissions and lifecycle; redact addresses in log/CI/PR artifacts; document deliberate revocation/clear flow.

### Android integration questions to prove offline

- Inspect actual Android 12 M3 OEM manifest and pairing receiver intent filters, permissions, priority, exported state and any other receivers; verify actual broadcast delivery semantics (do **not** assume `abortBroadcast()` works).
- Verify API and binder path for `BluetoothDevice.setPin(byte[])` (if present), binary byte length, necessary `BLUETOOTH_CONNECT` (Android 12 runtime / manifest) plus `BLUETOOTH_PRIVILEGED` or equivalent caller grants. Signature/privileged permission grant, privapp-permissions allowlist, platform signing, shared UID restrictions, SELinux and installation mode must be proven, not inferred from root.
- Distinguish a normal signed app, properly privileged system app, and root service. Direct calls to hidden APIs can be blocked by hidden-API enforcement. No blanket hidden-API exemptions or SELinux weakening.
- Determine whether helper can receive broadcast and issue exactly one authorized response without a race against OEM `TvSettings`. Verify that default global pairing behavior is preserved for non-DS3 devices.

## Minimum missing diagnostic: runtime variant

First review the existing sanitized historical log for explicit `PAIRING_VARIANT` or `min16Digits`; if absent, document a **single owner-approved, bounded, passive** pairing-intent observation plan to capture the integer variant and correlation time/device class without disclosing MAC/PIN. A temporary **non-privileged observation-only** receiver is useful *only if* Android actually delivers the broadcast to it; otherwise prefer approved log instrumentation at a supported boundary. Installation, pairing attempt, receiver enablement and any Bluetooth restart are separate approval gates. If actual variant is not 0 (or boolean is true), stop and reassess, don't submit a PIN.

## First implementation milestone (M1): host-side, no M3 runtime changes

Deliver:
- Tiny Android 12 module interface/spec for PIN decision: `{armed, controllerMatch, hostMatch, variant, min16Digits, deadline, permissions, deliveryExclusive} -> REJECT | READY_FOR_PIN`. A `READY` outcome is **not** automatic service execution.
- Pure offline tests: raw six-byte PIN golden vector and byte order, changed adapter/master, wrong controller, ambiguous identity, variant 7, stale/duplicate event, failed permission, no deterministic receiver routing, timeouts, unknown PIN source; all fail closed.
- Checked manifest sketch and permission/access matrix **without** installable privileged or boot-persistent package in this milestone.
- Sanitized device-side *future* observability: pairing variant, helper decision, API return, HCI reply, bond state, HID InputDevice and RetroArch only after successive approvals. No repeated USB functionality test.

## GO / NO_GO checkpoints

**M1 GO (build only)** when host-side validation contract, provenance, static permission/receiver analysis and reversible design are reviewed, and no APK is installed. **M1 NO_GO** for guessed PIN bytes/order, unverified API, receiver race, broad pairing policy, or any live service effect.

**M2 GO (separate Owner approval)** only after runtime variant is confirmed, binary PIN and per-controller USB enrollment are validated, deterministic privileged ownership is demonstrated, package signature/privapp grant and system-integrity handling are viable, and Wi-Fi/USB ADB recovery has been **independently verified**. Explicit new Owner approval required for installing APK, privileged placement, Settings disablement/replacement, Bluetooth restart, or one-shot pairing.

**Stop triggers:** variant !=0, unknown controller/host address, unmatched enrollment, permission denial, competing handler, duplicate request, failure to safely disarm, unexpected general pairing impact, loss of ADB/recovery, HCI error beyond narrow null-PIN hypothesis.

## Recovery and rollback (design, not authorization)

- Before any future device test: offline artifact hash, current package/permission/receiver baseline, independent Wi-Fi ADB and USB fallback validation, preservation of exact OEM APK and bootable recovery path, no auto-run on boot.
- Separate user-space disable/uninstall path from privileged system-placement rollback (which might require remount, verification/AVB considerations, reboot, and real device recovery). Do not label privileged APK deployment inherently reversible until demonstrated.
- On failure: stop new pair attempts, disarm helper, gather sanitized logs, restore receiver state if changed, and leave Bluetooth service untouched until operator-approved recovery. No automated service restart, firmware flash, injection, or global security policy edits.
- Post-test: verify baseline unrelated Bluetooth pairings and system health; do not expose LinkKeys, PIN, real MACs or proprietary APKs.

## Owner decisions / scope

- Firmware flash for 2025 International DS3 fix: **NO**.
- Built-in BT only; no external dongle/bridge.
- Native Bluetooth C4C-3 injection: **NO_GO**.
- This PR authorizes documentation/planning and offline tests **only**; does not authorize live modifications and must not merge without Owner approval.

References: Issue #6; Draft #48; merged-into-research-branch #49; earlier S8 #47; `AGENTS.md`, `docs/SAFETY.md`.
