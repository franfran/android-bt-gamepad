# C4C-3 Android 12 namespace selection — static assessment

**Decision: NO-GO for production Bluetooth calls.** This assessment analyzes
already collected, read-only static evidence, not the dynamic linker state
of an existing process. It does not authorize Bluetooth attach, restart,
injection, policy change, or an add-on load.

## Evidence from M3

Owner ran the fixed read-only linkerconfig inspector on M3. Two candidate
configuration files were readable; both collectively exposed configuration
sections, directory mappings and namespace keys. No raw path policy was
submitted or retained. The report expressly left process namespace
selection, add-on path permission and actual loader acceptance UNVERIFIED.

Other independent observations: Bluetooth identity and UID 1002, 48 threads,
mapped Bionic linker and Bluetooth library; Wi-Fi ADB baseline working.
USB ADB was separately confirmed in normal conditions as last-resort fallback.

## How selection works — with essential caveat

AOSP documents a generated linker configuration under `/linkerconfig`.
For a **native executable** using the standard linker config, entries of
form `dir.<section>=<executable-directory>` map executable locations to
configuration sections `[section]`, which then define namespace search,
permitted paths, isolation and namespace link rules. Section match therefore
requires the **actual executable launch path**, not the `comm` name
(`droid.bluetooth`) or an ordinary loaded .so from `/proc/PID/maps`.

**Critical Android app-process distinction:** `com.android.bluetooth` may
be zygote-forked / app-managed on an OEM build. The native executable's
bootstrap namespace and later app classloader namespaces need not be the
same, and call-site linkage can affect `dlopen` visibility. Neither a
guessed `/system/bin` section nor the presence of `libbluetooth.so`
identifies the namespace used by a given service call. The active process
could use vendor-specific mechanisms. Mark these claims UNVERIFIED without
an authoritative process launch and linkage trace.

## What we can infer from the current M3 report

| Hypothesis | Measured? | Implication |
| --- | --- | --- |
| Android generated static policy exists | YES (2 candidate files) | Supports further offline policy inspection |
| At least one directory-to-section mapping exists | YES | Not a mapping *to Bluetooth* |
| Namespace keys exist | YES | No proof of Bluetooth default or classloader namespace |
| Bluetooth uses a particular native executable section | NO | Need trusted launch provenance and config file precedence |
| Bluetooth is permitted to load the staged /data/local/tmp add-on | NO | Need exact applicable namespace, search/permitted paths, dependencies, filesystem and SELinux checks |
| Real service can safely call Bionic dlopen | NO | Separate threading, linker locks, recovery and test-target-wrapper gap |
| Wi-Fi ADB survives a Bluetooth crash | NO | Normal-state readiness only; USB fallback works only as separately observed |

## Offline-only decision procedure for a later reviewed analysis

1. **Identify actual launch provenance** (native executable or zygote
   managed process) from known build metadata, init service definition or
   sanitized read-only process metadata. Do not assume process `comm`
   equals executable path. If ambiguous, record `launch_origin=UNKNOWN`.
2. **Determine configuration precedence and environment** for the process:
   generated linkerconfig in use, launch mount namespace and APEX
   context; note alternative files. Do not claim the first readable file
   must be the active one.
3. **Only if a native executable and selected config are established,**
   compare executable directory to `dir.<section>` prefixes using path
   boundaries (not raw string prefix). Multiple matches/conflicts require
   manual review, not choosing an arbitrary first match.
4. **Distinguish bootstrap default namespace from caller namespace.**
   App classloader / libnativeloader behavior and vendor linker customizations
   can change which namespace applies to calls. Without proof of call
   origin, retain `caller_namespace=UNKNOWN`.
5. **Offline policy review:** examine isolation, search and permitted paths,
   namespace link lists and dependency visibility in a private workspace.
   Even a plausible path permit is only **INFERRED**, never a proven runtime
   `dlopen`. Redact serial, complete maps, MAC and memory addresses.
6. **Stop at the read-only boundary**: no `dlopen`, `linkerconfig`
   regeneration, service restart, runtime linker inspection by injection,
   copy into privileged paths or SELinux edits.

## Next single useful evidence request

Obtain a **sanitized launch-provenance classification** for the running
Bluetooth process (native executable vs zygote/app-managed vs unknown),
with confidence and source, and the identity of the active config source.
If that information cannot be established read-only on M3, document
`UNKNOWN` and stop; further static Boolean checks will not close the gate.

The previous C4B resolver's address calculation is independent of
namespace permission. It must not be used as a positive namespace result.

## References

- [AOSP Android 12 linkerconfig README](https://android.googlesource.com/platform/system/linkerconfig/+/refs/heads/android12-mainline-resolv-release)
- [AOSP Bionic linker config format](https://android.googlesource.com/platform/bionic/+/ec829ed4ea3e0b2e1444ee4dfef660c49e392292/linker/ld.config.format.md)
- [Android linker namespace architecture](https://source.android.com/docs/core/architecture/vndk/linker-namespace)
- Repository: Issue #6 and draft PR #11.

**No merge or live experiment is authorized by this document.**
