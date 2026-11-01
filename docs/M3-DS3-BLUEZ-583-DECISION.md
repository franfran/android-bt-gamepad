# DS3 M3 — Revised implementation decision: BlueZ 5.83 cable pairing

**2026-10-31, offline review only.** This replaces the outdated assertion that a safe Sixaxis cable-pairing solution exists only as a BlueZ proposal.

## Confirmed upstream development
- **BlueZ 5.83** (release June 2025) changelog explicitly includes "Fix issue with handling cable pairing and Sixaxis controllers": https://kernel.googlesource.com/pub/scm/bluetooth/bluez.git/+/refs/tags/5.83%5E%21/
- BlueZ Device D-Bus API documents **CablePairing**: cable-paired device not supporting normal encrypted bonding (Sixaxis); connection established without enforcing encryption: https://manpages.ubuntu.com/manpages/resolute/man5/org.bluez.Device.5.html
- The BlueZ design is to maintain default bonded-only security for other devices while handling USB-registered Sixaxis selectively. See https://github.com/bluez/bluez/issues/1165 . Do **not** globally disable security.
- Upstream contributor's 2025 commit discussion explicitly says Sixaxis/PS3 controllers **aren't paired** (normal link-key bonding): https://www.spinics.net/lists/linux-bluetooth/msg122746.html
- macOS ds3activate's zero-length *delegate* reply is **not** a valid substitute for BlueZ cable-pairing admission and doesn't imply Android Java `setPin(null)` will work.

## Actual device baseline
The user re-uploaded `M3-Bluetooth.apk.zip`; original APK SHA-256 `d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f` matches previous M3 2024 / 2025 source evidence. Archived exact-M3 HidHostService.okToConnect(bytecode code_off 0x26e880) has an explicit `getBondState(peer)==12 BOND_BONDED` admission condition, plus policy -1 or 100 and quiet-mode checks. This is an **actual vendor Java HID gate**, not merely AOSP reference. S8 static native findings demonstrate a route from incoming L2CAP HID to HCI 0x0411 Authentication Requested. Those results are static and cannot establish all runtime branches.

## Architecture decision
**Recommendation: pursue BlueZ 5.83-style USB-cable-pairing authorization as a design reference, but do not install BlueZ, change Android's global security, fake a link key or bond state, or claim it is supported by M3.** The unchanged M3 has (1) native security requirement and (2) explicit Java `BOND_BONDED` gate. To make the nonbonded path possible, a proper scoped M3 integration would have to address **both**, with exact per-controller enrollment/provenance, input-report restrictions and meaningful revocation.

**GO:** small offline-only implementation design for a narrowly-scoped explicit cable-paired controller admission model (data structures, policy predicate, fake-device rejection tests, mapping to native PSM and HID Host gate). **NO_GO:** PIN-only helper, empty PIN trial, global unbonded HID, system package replacement, binary patch, ptrace/dlopen live injection. C4C-3 NO_GO unchanged.

## Deferred engineering gates
1. Verify exact vendor bytecode for any existing supported USB cable-pairing / per-device trusted HID authorization. Absence of proof ≠ proof none exists.
2. Verify precise native security callsite has controller address + PSM available *before* auth gate. Do not claim blanket HID exception from callsite lacking device context.
3. Derive minimal patch surfaces and rollback / privilege / signature / AVB risk on owner-original artifacts; keep any code offline.
4. No live install, Bluetooth service restart, DS3 attempt or security policy change without explicit Owner approval.

## Corrected prior assumption
The previous speculative "six-byte host MAC as PIN" and "zero-length PIN may avoid patch" are not validated. BlueZ cable pairing is an authorization architecture, not a choice of secret PIN bytes. Real DS3 compatibility must also reach Android InputManager, with bounded handling of PS3-specific HID reports.
