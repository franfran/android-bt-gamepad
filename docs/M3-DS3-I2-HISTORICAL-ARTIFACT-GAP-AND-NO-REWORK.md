# I2 historical artifact availability and branch decision

Research-only review, 2026-11-01 Toronto. No new runtime telemetry.

## Audited sources
- [PR #50 changed-file inventory](https://github.com/franfran/android-bt-gamepad/pull/50/files) includes research markdown, host-only test models, and read-only collection scripts. The inventory did **not** include an identifiable raw continuous HCI btsnoop/logcat capture file. Absence in changed-file inventory does not rule out earlier archived data elsewhere or GitHub issue attachments.
- [PR #50 S7/S8 integration contract](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-S7-S8-INTEGRATION-CONTRACT.md): previously considered a plugin carrying per-device decisions, but runtime interception/loader and separate Java gate were unresolved. Incoming L2CAP callsite has address + PSM in original M3 ELF, but an ELF VMA is not a supported dynamic hook.
- [PR #50 dual channel validation](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-DUAL-CHANNEL-VALIDATION.md): host simulation does not establish actual controller authentication.
- [PR #50 Bluetooth operational mode](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-BLUETOOTH-OPERATIONAL-MODE.md): synthetic validity flags are not credentials or runtime proof.
- [PR #50 pairing implementation plan](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-PAIRING-IMPLEMENTATION-PLAN.md): reports missing PIN replies historically but does not provide fully correlated timing and PIN-variant observation for the same 0x22 attempt.

## Evidence gap / STOP
Cannot infer same-session causality of PIN request, absence of PIN response, HCI auth completion 0x22, native HID open/close, Java admission, or kernel UHID from current reviewed material. Source registration and model tests cannot fill that gap.

## Avoid duplicated research
PR #50 already determined: a loadable policy module does not grant supported Fluoride interception; native hook/injection route is NO_GO; Java PIN helper alone cannot guarantee native HID connection. PR #52 should investigate supported integration, not repeat S7 injection strategies.

## Next minimal action
Before any new pairing attempt, check whether sanitized timestamped captures exist in other earlier evidence/issue attachments (not reviewed here). If absent, draft a passive one-attempt observation protocol with explicit prior owner consent and no environment modifications or PIN intervention; define event correlation by per-run monotonic clock and ephemeral peer/session ID. No live device operations authorized.

## Architecture checkpoint
A: third-party drop-in plugin—no supported extension proven.
B: standalone daemon—controller/PSM ownership unresolved.
C: minimal in-stack adapter—source seam conceivable, but native security root cause, Java admission, UHID identity and OEM build integrity all unresolved.
D: interop/PIN-only—insufficient as a complete solution.
