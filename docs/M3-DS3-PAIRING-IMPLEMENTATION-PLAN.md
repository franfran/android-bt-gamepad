# M3 DS3 Legacy PIN — Implementation Architecture and Validation Gates

**Status:** planning-only Draft PR; upstream BlueZ research makes nonbonded USB-enrolled HID the first architecture question, before any PIN helper. **Target:** iMETBOX M3 International, Android 12 API 31, Allwinner H618, built-in Bluetooth. **No device modifications authorized.**

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

**IMPORTANT:** DS3 legacy PIN may be six **raw** bytes representing the Bluetooth host adapter BD_ADDR, was an initial hypothesis, **not established for DS3 PIN response**. Published BlueZ `sixaxis.c` confirms host BD_ADDR is written into controller using USB feature report 0xF5, but this is **enrollment**, not a proof the subsequent PIN equals host BD_ADDR. `ds3activate` macOS `devicePairingPINCodeRequest` explicitly replies with zero-length PIN (platform-specific and not proof Android/HCI accepts it). Some implementations avoid ordinary PIN/bonding and instead arrange USB-authorized HID trust. Determine the **actual DS3 pairing mechanism** and supported Android path before proposing bytes. Reject ASCII `0000`, MAC-as-PIN, zero-length, or any other PIN guess until supported by an independently verified applicable implementation. Never commit the host/controller MAC, PIN, LinkKey, bond DB or raw HCI log.

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
4. PIN handling remains **unresolved**; do not conflate `0xF5` host master BD_ADDR enrollment with HCI PIN reply. Compare BlueZ Sixaxis USB authorization/HID setup and macOS zero-length PIN callback. Classify the M3 path as `PIN_REQUIRES_VERIFIED_IMPLEMENTATION`, not `READY_FOR_PIN`, until a proven Android-compatible mechanism exists. Reject speculative PIN values or format.
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
- Pure offline tests: controller/host address byte-order for **USB enrollment only**; fail-closed unknown/empty/MAC/PIN attempts; changed adapter/master, wrong controller, ambiguous identity, variant 7, stale/duplicate event, failed permission, no deterministic receiver routing, timeouts, unknown PIN source; all fail closed.
- Checked manifest sketch and permission/access matrix **without** installable privileged or boot-persistent package in this milestone.
- Sanitized device-side *future* observability: pairing variant, helper decision, API return, HCI reply, bond state, HID InputDevice and RetroArch only after successive approvals. No repeated USB functionality test.

## GO / NO_GO checkpoints

**M1 GO (build only)** when host-side validation contract, provenance, static permission/receiver analysis and reversible design are reviewed, and no APK is installed. **M1 NO_GO** for guessed PIN bytes/order, unverified API, receiver race, broad pairing policy, or any live service effect.

**M2 GO (separate Owner approval)** only after runtime variant is confirmed, the DS3 authentication method (not simply its USB host-address setup) and per-controller USB enrollment are validated, deterministic privileged ownership is demonstrated, package signature/privapp grant and system-integrity handling are viable, and Wi-Fi/USB ADB recovery has been **independently verified**. Explicit new Owner approval required for installing APK, privileged placement, Settings disablement/replacement, Bluetooth restart, or one-shot pairing.

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

## Community source correction (2026-10-31)

- BlueZ `plugins/sixaxis.c` uses USB HID feature report `0xF5` to get/set the **central/master host Bluetooth BD_ADDR** and `0xF2` to identify controller; this is established cable enrollment, not evidence for a six-byte Legacy PIN response. Source: https://kernel.googlesource.com/pub/scm/bluetooth/bluez.git/+/a93047cd044fb17d687f43bef95289ec834876b2/plugins/sixaxis.c
- `crux161/ds3activate` calls `replyPINCode:0 PINCode:&pin` in its macOS pairing delegate. A zero-length reply is a platform-specific example; it does **not** establish M3 Android BluetoothDevice.setPin supports length zero nor guarantee successful DS3 authentication. Source: https://github.com/crux161/ds3activate/blob/main/ds3activate.c
- Community Linux guides report BlueZ `ClassicBondedOnly=false` workarounds after CVE-2023-45866 changes. Such a **global security relaxation is prohibited on M3**. Sources: https://wiki.archlinux.org/title/Gamepad and https://github.com/bluez/bluez/issues/688
- Revised M1 gate: **first select and prove the DS3-specific authentication approach from mature implementations; no hardcoded six-byte PIN proposal**. The old host-address-as-PIN assumption must not be implemented.


## Community upstream design changes priority — BlueZ issue #1165 (2025)

**Source:** https://github.com/bluez/bluez/issues/1165

The BlueZ Sixaxis maintainers discuss why simply weakening `ClassicBondedOnly` globally is unsafe (CVE-2023-45866), and propose **USB-enrolled-controller-specific HID admission** while preserving the default policy for all other devices. They report `BT_IO_SEC_MEDIUM` forces encryption/bonding and may trigger a PIN the DS3 does not expect. This is an upstream discussion, **not** an implemented Android patch or proof of the exact M3 native path.

**Design implications:**
1. Treat M3's missing PIN reply as an observed symptom, not yet proof that supplying *any* PIN will solve DS3 Bluetooth HID. An empty/zero-length PIN in macOS `ds3activate` is a macOS pairing delegate call; it does not establish an M3 HCI or Java solution.
2. Move **DS3-specific USB-enrollment-gated HID authorization, without normal PIN bonding**, ahead of the privileged PIN helper in the alternatives study. Determine whether M3's Fluoride/Android stack has an existing supported per-device policy/hook at a suitable layer; don't assume BlueZ APIs apply to the Allwinner HAL.
3. Maintain the no-global-security-relaxation rule: no `ClassicBondedOnly=false` equivalent globally, no bypass for unknown MAC/name/CoD, no unauthorized keyboard/HID admission. A previously observed controller MAC alone is spoofable; account for impersonation and HID report restrictions.
4. Offline M1 now includes a **protocol decision matrix**: (A) normal PIN bonding, (B) zero-length PIN response, (C) USB-enrollment-authorized nonbonded HID, with direct source evidence and Android API availability. No path is assumed proven on M3.
5. If M3 security/authentication requires a native per-connection exception but has no supported integration, the existing C4C-3 live injection NO_GO **still wins**. Do not represent a Bluetooth PIN receiver as equivalent to disabling the native security request.
6. Any runtime diagnostic/connection attempt still needs explicit Owner approval. No device operations were performed.

**Android SDK nuance:** `BluetoothDevice.setPin(byte[])` exists in the official Android API and Android 12 normally requires `BLUETOOTH_CONNECT`; exact OEM permission checks and acceptance of an empty array must be verified. Never substitute `setPin(null)` for an empty byte array. Documentation: https://developer.android.com/reference/android/bluetooth/BluetoothDevice .


## Android HID Host second gate — community/AOSP cross-check (2026-10-31)

**Primary sources:**
- BlueZ issue https://github.com/bluez/bluez/issues/1165 (proposed **not proven shipped** per-Sixaxis authorization; discusses L2CAP `BT_IO_SEC_MEDIUM` and PIN/encryption mismatch; acknowledges spoofing risk).
- Android HID Host `okToConnect()` reference https://android.googlesource.com/platform/packages/apps/Bluetooth/+/refs/heads/master/src/com/android/bluetooth/hid/HidHostService.java (rejects non-bonded devices).
- Historical AOSP alternative https://android.googlesource.com/platform/packages/apps/Bluetooth/+/bc8794046cb965d99d0623c75d5e0e783a56a6ca/src/com/android/bluetooth/hid/HidHostService.java (different bond-state condition).
- Current modern Android modules Bluetooth source has further changes; do **not** assume exact applicability to M3 2024 vendor Android 12.

**Consequence:** A privileged receiver fixing `setPin(null)` is **not sufficient proof of success**. M3 potentially enforces *two independent admission gates*: native L2CAP/BTM security before HID control/interrupt establishment, and Java `HidHostService.okToConnect` enforcing bonded state. Exact M3 implementation of the latter must be verified before suggesting a patch (the referenced upstream source is not M3 vendor code). A missing HCI reply may simply be the observable consequence of a DS3-incompatible bonding requirement; a nonbonded exception must still be scoped securely. Do not manufacture a BOND_BONDED state or forge LinkKeys.

**Required offline decision tree (next milestone):**
1. From owner-original M3 `Bluetooth.apk` bytecode, locate actual `HidHostService.okToConnect`, bond check, connection priority/policy, and any vendor-supported per-device admission path; evidence code offsets and reference SHA only, **no vendor APK commit**. Clearly mark not found / uncertain.
2. From existing original M3 native traces, map the *known* incoming HID PSM 0x11/0x13 → security-level request → HCI Authentication Requested boundary. Don't redo broad S8 reverse engineering; use existing S8 proven call edges. Determine if a Java API can influence this security request **before** the native gate (not after).
3. Compare possible (a) valid legacy PIN bonding, (b) nonbonded USB-authorized HID, (c) unsupported/no safe integration. Exactly identify which gates each would satisfy. `BluetoothDevice.setPin()` cannot be claimed to override L2CAP security level.
4. If both gates lack supported per-device integration, classify standalone-helper-only as **NO_GO**, prepare a narrowly scoped native+HID policy design for Owner review *without implementing risky injection*. Revisit only after explicit separate authorization and recovery readiness; C4C-3 NO_GO persists.
5. Explicitly disallow Android-wide unbonded HID acceptance or BlueZ `ClassicBondedOnly=false` analogue. Address-spoofing, fake keyboard injection, and audit requirements are mandatory.

**First implementation milestone clarification:** M1 is now offline **two-gate feasibility proof**, not APK scaffolding. Runtime DS3 variant capture remains optional until the selected architecture actually relies on supplying a PIN. Avoid a fresh pairing attempt merely to test the old null-PIN hypothesis.
