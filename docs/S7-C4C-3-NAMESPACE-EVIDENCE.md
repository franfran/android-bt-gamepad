# C4C-3 — Android Bluetooth linker namespace: read-only evidence decision

**Review only; no Bluetooth service execution, attach, restart or injection.**
Issue: [#6](https://github.com/franfran/android-bt-gamepad/issues/6).
This is a *static inference worksheet*, not a namespace-acceptance test.

## Known facts and inference limits

- The owned M3 Bluetooth service is an Android 12 ARM32 process whose mapped
  libraries and process identity can be inspected read-only. C4B and the
  C4C-3 health checker have shown expected identity, library mappings, UID
  and thread count. Those observations prove *mapping and process health*
  at the observation time, **not** that the process's dynamic linker will
  accept a new library from a different directory.
- The previous independent `rbxc4c_target` test used its own
  instrumented loader wrappers. Its successful `dlopen` is **not**
  evidence that `com.android.bluetooth` can call `dlopen` on the
  staged add-on, or that such a call can be rolled back.
- Android linker namespace decisions can depend on the process launch
  context, classloader/native-loader configuration, namespace links,
  permitted paths, accessible libraries and dependency visibility. On an
  OEM build, neither generic AOSP behavior nor `/proc/PID/maps` alone
  establishes those rules for the active process. SELinux and file
  access checks are additional constraints, not substitutes for linker
  namespace checks.

## Minimum evidence table

| Item | Collection method (read-only, bounded) | What it can establish | Cannot establish |
| --- | --- | --- | --- |
| Bluetooth process identity, UID, status and mapped libs | Existing C4C-3 health checker | Process/mapping baseline | Namespace permission for new library |
| Existing mapped linker/libdl | Process maps, restricted to aggregate flags in public output | Dynamic linker present | Which namespace handles a particular call |
| Staged add-on path/hash | Existing C4A/C4B private inventory if files remain staged | Byte identity | Linker access or dependency resolution |
| Linker config files | Owner local read-only inspection of relevant runtime/system/apex configs | Candidate policy inputs | Which exact namespace the running service actually uses |
| Process launch/namespace provenance | Reviewed build-time init and loader configuration, if accessible | Likely namespace creation path | Proof of specific runtime `dlopen` acceptance |
| Namespace success/failure in real Bluetooth | Would require target-context execution | Direct acceptance result | **Not allowed in C4C-3** |

**Classification rules:** each item must be marked MEASURED, INFERRED or
UNVERIFIED. Even a complete read-only snapshot may only support
`namespace_policy_inferred` and must leave
`linker_namespace_acceptance=UNVERIFIED`.

## Gap review of existing C4B tooling

`experiments/s7-c4b/s7c4b.py` resolves the runtime symbol from an ELF
and PID-specific mappings; it does **not** perform a namespace check.
It also reads complete mapping text and library bytes and outputs PID,
addresses, hashes and paths. Those are *private-only raw artifacts*,
unlike the deliberately sanitized C4C-3 health JSON. Do not paste raw
C4B output to public issues. Its hard-coded blocker language about
missing return trampoline predates successful **test-target-only**
trampoline work, and must not be interpreted as a fresh production result.

A namespace evidence collector should **not** attempt to run
`linkerconfig`, `dlopen`, modify namespaces, copy/link an add-on into
a privileged location, weaken access-control policies, or use process
injection as a read-only shortcut.

## Non-disruptive operator evidence sequence

1. Preserve the known-good Wi-Fi ADB session. Treat separately observed
   USB ADB as last-resort fallback, **not** a required connection during
   each read-only check.
2. Reuse the passing, sanitized C4C-3 health baseline. On unexpected
   identity, mapping or transport changes, stop rather than retry.
3. Review available *static* process launch and linker configuration
   evidence privately. If file access fails or required context is not
   available, record `UNVERIFIED` rather than changing any policy.
4. Summarize only policy file presence, high-level namespace constraints
   and confidence in the inference. Do not publish raw process maps,
   addresses, serials, vendor binaries or pairing data.
5. Make a separate owner-reviewed decision on whether this inferred
   information justifies further **isolated, owned-process** experiments.
   It does not directly authorize any live Bluetooth operation.

## Risk decision and stopping conditions

**Current C4C-3 status: NO-GO.** Existing M3 read-only health and
Wi-Fi readiness passes are useful evidence of a normal-state baseline.
They do not verify transport survivability during failure, linker
namespace acceptance or an independently rehearsed Bluetooth recovery
procedure. An in-flight Bionic linker stall cannot be safely reversed
just by restoring registers. Do not use a successful CI test or this
document as permission for a production call.

**Next measurable outcome:** a sanitized inventory of static policy
*inputs*, with explicit uncertainty labels and an operator review.
Only an independently authorized future phase may consider a
service-context experiment.
