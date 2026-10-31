# S7-C4C plugin research vs M3 DS3 policy hook — integration decision

**2026-10-31 — offline design only.** Owner correctly pointed out earlier research on a native plugin. This is directly relevant and **must not be reinvented**. References: `AGENTS.md`, `docs/S7-C4C-HANDOVER.md`, `docs/SAFETY.md`, Issue #6, PR #3/#4/#5, and S8 native event/PSM findings PR #32/#38/#39/#40.

## Terminology: three separate engineering layers

1. **Plugin/add-on artifact:** an ARM32 `.so` (`libretrobox_ds3_addon.so` was staged) containing code. Its existence says nothing about Bluetooth compatibility.
2. **Loader:** safely mapping `.so` into a running process via `dlopen` or another supported loading mechanism, including linker namespace, process/thread safety, return trampoline, and rollback. This was investigated in S7-C4C.
3. **Policy hook/integration point:** getting an actual Bluetooth decision to invoke the loaded code at the correct time with peer/PSM context. A library mapped in memory does **not** hook any function, authorize HID, or modify security behavior by itself.

A **supported callback/plugin API** would be preferable to inline patching or function detours. No such publicly callable OEM Bluetooth extension has been verified. Android's ordinary app/plugin concept is not equivalent to Bluetooth service native hooks.

## What is already genuinely proven (do not repeat)

- S7 isolated/fork-owned or independently launched **test** processes: ARM32 target-private scratch, RX trampoline, symbol/ASLR resolution, `dlopen` success/failure handling, thread progress, signal and timeout quarantine. PR #3/#4/#5 record actual M3 **owned-test-process** results. This is substantial engineering progress.
- S7-C4B actual Bluetooth service read-only: identity/hash/maps/thread checks and staged inert add-on SHA; `addon.mapped=false`, `injection_authorized=false`.
- S8 exact owner ELF: incoming L2CAP security caller carries remote address + PSM and can initiate HCI Authentication Requested conditionally. The Java HID Host independently demands `BOND_BONDED`.

## What plugin research DOES NOT prove

- Safe execution of a remote `dlopen` in **actual** `com.android.bluetooth` with ~48–49 live threads.
- Linker namespace permission for loading a library from its staged path under target's actual context.
- Target-specific clean return/recovery if `dlopen` stalls, runs constructors, takes linker locks, or partially changes process state.
- Any registered native policy callback, trampoline/interposer/detour, or Java HID Host modification.
- A safe way to unload injected code (removing staged file does not unmap it).
- A path through two independent DS3 admission gates.

All above stay **UNVERIFIED**; S7-C4C-3 live injection remains **NO_GO**.

## Preferred implementation exploration sequence

**Track A — supported integration first:** inspect original M3 platform APIs / plugin-loading conventions / HID Host and native stack for an OEM-supported policy interface; demonstrate callability offline with source/DEX/ELF evidence. If one exists, prefer it and avoid ad-hoc `ptrace`.

**Track B — reuse S7 as a conditional fallback:** only if the required native policy cannot be reached using supported interfaces, map the **existing S7 add-on/loader research** to the new S8 decision boundary. Define exactly how code is invoked during incoming Classic HID and how the separate Java gate is met. This is a *design exercise*, not authority to inject. Do not rebuild the S7 trampoline from scratch.

**Track C — safer non-injection patch:** assess an offline exact-firmware source/bytecode-level modification with reproducible build, signature, privileged placement, boot recovery and rollback. This may be safer or riskier than injection depending on verified boot and OEM keys; do not assume writable system partitions or safe rollback.

## Decision table

| Mechanism | Solves loading? | Solves policy hook? | Solves Java HID gate? | Current status |
| --- | --- | --- | --- | --- |
| S7 test-owned `dlopen` | Proven **only in test process** | No | No | Valuable foundation; not deployment |
| Staged inert native add-on | Not loaded in BT process | No | No | No live permission |
| Safe exported OEM policy callback | If actually exposed | Potentially | Needs separate integration | Not verified |
| Privileged Java pairing receiver | Does not load native hook | No pre-auth native control | No guaranteed genuine bond | PIN-only NO_GO |
| Rebuilt platform Bluetooth package | Could avoid runtime injection | Only if exact patches worked | Also needs targeted Java policy | Offline design only |

## Minimal next milestone — avoid another broad reverse-engineering loop

- Produce an **explicit S7-to-S8 interface contract**: desired hook arguments (peer, PSM, incoming direction, authorized enrollment decision), exact native caller with retained context, decisions and default fallback, and no effect on unrelated Bluetooth devices.
- Keep existing S7 hardware validations as completed; enumerate *only missing* production-service loader/hook safety proofs.
- For each potential integration, note whether it requires system privilege, Bluetooth process restart, signature keys, on-device install, and independently verified rollback.
- Source-only tests may be run in isolation; no M3 Bluetooth service action or permission downgrade without new Owner authorization.

## Owner and acceptance

Owner allows **one-time USB enrollment** already completed; DS3 must subsequently connect via **M3 built-in Bluetooth** after pressing PS and work wirelessly in RetroArch. USB gameplay and mapping are already PASS, not to be retested. No dongle, bridge, firmware flash, broad PIN guess, fabricated bond or global security relaxation.

**No merge and no live modifications without explicit Owner approval.**
