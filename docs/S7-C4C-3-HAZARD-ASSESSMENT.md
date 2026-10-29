# S7-C4C-3 — Live Bluetooth hazard assessment and independent recovery gate

**Status: DESIGN REVIEW ONLY · NO-GO for any live Bluetooth code execution.**
This document follows [Issue #6](https://github.com/franfran/android-bt-gamepad/issues/6). Its statements distinguish **measured** device results, **inferences** and **unverified** requirements. The document does not grant permission to inject or restart the Bluetooth service.

## 1. Verified evidence and provenance

| Subject | Evidence class | Status | Reference / limitation |
| --- | --- | --- | --- |
| Independent ARM32 48-worker target normal remote load, private scratch, canaries, RX return trap, unmap | Measured M3 | PASS | PR #3, compiled test target with built-in return trap |
| Test-image ARM SVC tagged syscall bootstrap for mmap2/mprotect/munmap; test dlopen/dlerror | Measured M3 | PASS | PR #4, still calls exported test-target wrappers; no Bluetooth execution |
| Fixed SIGUSR1 delivery-stop quarantine and nonreturning-function timeout quarantine, scoped test kill and runner cleanup | Measured M3 | PASS | PR #5, both separate owner runs; deliberately **no dlopen during faults** |
| Bluetooth UID 1002, comm `droid.bluetooth`, 48–49 threads, dynamic PID, legacy Fluoride stack | Prior read-only measurement | Previously observed, refresh required | `docs/STATUS.md`, `experiments/s7-c4b/` |
| Staged inert addon bytes and hash, `addon.mapped=false` | Prior read-only measurement | Historical only, refresh required | S7-C4A/B; staging is not loading |
| Correct runtime `dlopen` Thumb address from ELF / maps | Prior read-only measurement | Historical only, refresh required | S7-C3 resolver and S7-C4B; recompute for every snapshot |
| Bluetooth's linker namespace accepts `/data/local/tmp/retrobox_s7c4_inert/` | Unverified | **NO-GO** | Shell test target runs in a different namespace |
| Independent access when Bluetooth service becomes unresponsive | Unverified | **NO-GO** | Need operator-confirmed USB/wired ADB, not solely Bluetooth or network assumptions |
| Recovery of an in-flight or deadlocked Bionic `dlopen` | Unverified | **NO-GO** | Killing an owned test executable is not proof of recovering another service |
| Safe real-service function return, concurrent linker locks, signal delivery and thread effects | Unverified | **NO-GO** | Test thread synchronization and service state differ |

Do not reuse historical PIDs, load bases, function pointers, staged hashes or device addresses. No MAC, PIN, LinkKey, home IP or extracted vendor binary belongs in committed evidence.

## 2. Linker namespace / process execution boundary

Android's linker namespace membership and permitted search/permitted paths are process-context dependent. A read-only `/proc/PID/maps` snapshot or success of `dlopen` from a root test executable proves neither permission for the Bluetooth process to load an add-on from `/data/local/tmp` nor safety of entering the linker.

Before any GO decision, independently establish the applicable target namespace rules, target ELF/build ID, loaded Bionic linker/libdl mappings, exact add-on path/hash and failure behavior. Mark **UNKNOWN** where only static config or shell-process experiments exist. Do not change SELinux, Bionic linker configuration, global security policy or move arbitrary libraries to privileged locations as a workaround.

**Unimplemented production parity:** PR #4 uses `rbxc4c_load` and `rbxc4c_error` symbols compiled into the test target. Bluetooth does not provide those wrappers. Real linker calls also use a live thread's normal call stack and thread-local linker state; the private argument scratch is *not* a replacement for stack/linker/TLS safety.

## 3. Thread and failure-state hazard model

| Phase | Possible risk | Safe policy / evidence needed |
| --- | --- | --- |
| Pre-attach/read-only | PID recycling, process change, ASLR and ELF drift, permission mismatch | Re-verify identity, UID, thread count, executable mapping, ELF digest before and after observation; abort on change |
| Attach/stop | Stopping a thread that holds or awaits a linker lock; signal delivery changes | No production attach in this gate; obtain independently reviewed concurrency policy |
| Before entering linker | Wrong return address, ARM/Thumb state, stack alignment, scratch or guard-page errors | Fail closed; no production remote calls approved |
| During `dlopen` | Constructor/loader stalls, locks held by other service threads, partial internal state | **INDETERMINATE QUARANTINE**; neither register restoration nor a deadline is a safe rollback |
| After returned load | Mapped module may persist, library initializers may have changed process state | Verify service health and mappings if authorized later; deleting staged file does not unload mapping |
| Service disruption | Bluetooth loss, controller state drift, device inaccessible over its usual channel | Need independent operator access, service recovery rehearsal and documented physical fallback |

**NO-GO triggers:** missing independent access, missing/rejected snapshot data, ambiguous PID/ELF identity, namespace unknown, unverifiable service restart/control, any unexpected process change, missing owner-approved recovery conditions, or an unclassified signal/linker state. Never auto-retry an indeterminate remote linker call; never call a global authentication bypass a DS3 fix.

## 4. Independent recovery requirements (operator checklist; DO NOT RUN YET)

- [ ] Confirm **physical wired USB ADB or equivalent independent channel** that remains connected when Bluetooth is disabled or crashed; record only a redacted test result.
- [ ] On that channel, independently measure Bluetooth process health and service state before disruption; confirm reidentification after a *benign*, owner-approved test, without performing a restart here.
- [ ] Define the exact owner-local, platform-appropriate service restart mechanism and expected collateral effects; have a second operator-approved recovery route when restart fails. Keep device power access.
- [ ] Specify post-recovery checks: service process UID/name newly resolved, thread count, adapter functional state, unrelated Bluetooth devices remain usable, no unexpected injected map, no persistent boot hook or filesystem change.
- [ ] Document how to preserve private logs outside public GitHub; report only sanitized state transitions and SHA-256 of evidence if needed.
- [ ] Define a one-shot authorization record (device identity privately, head commit SHA, observed target snapshot, test-only inert add-on hash, recovery channel and owner acceptance). Reauthorize from scratch after any change.

The above are **requirements**, not tests already completed. Never run a disruptive Bluetooth restart or attach during C4C-3 review. Reboot / service restart may release memory mappings but does **not** guarantee internal state rollback or data integrity.

## 5. Read-only evidence acquisition plan

Prefer existing `experiments/s7-c4b/s7c4b.py` and S7-C3 resolver as the starting point **after reviewing their exact flags and output sanitization**. The previously verified C4B output deliberately has `injection_authorized=false`. Any new gatherer must be read-only, bounded, explicit-ADB-serial, fail closed on PID/snapshot races, and omit sensitive identity from public logs.

Evidence to record: observation timestamp, whether an independent transport was used, process identity/UID/SELinux label, PID and thread-count only in private raw output, target executable/mapping Build IDs and hashes, actual loaded linker paths, sanitized namespace rule references, staged add-on digest/path, and whether each observation is measured versus inferred. Do **not** assert namespace acceptance from maps alone. Any apparent namespace test requiring execution inside live Bluetooth is *outside* this gate.

## 6. Decision record

**C4C-3 decision as of 2026-10-28: NO-GO.** We can now classify normal test-target execution, unexpected SIGUSR1 and deterministic nonreturning-call timeout. We **cannot** infer Bluetooth service recovery, namespace acceptance, production-safe call/return semantics or DS3 wireless pairing. The next useful step is owner-reviewed **read-only evidence + independent wired recovery control**, not injection.

A future C4C-4 trial would require separate written owner consent and a reviewed, target-specific one-shot plan. No implicit authorization follows from a passing CI run or a test target's successful `dlopen`.

## Read-only operator baseline (2026-10-28)

The owner executed the fixed `experiments/s7-c4c-health/read-only-health.py` on M3 through existing Wi-Fi ADB and supplied sanitized JSON. Verified: Bluetooth process identity, UID 1002 match, 48 threads, no tracer, mapped `libbluetooth.so`, Bionic runtime/linker mapping present, RetroBox add-on not mapped. **No PID, MAC, full mappings, local IP or raw logs are included here.** This establishes a useful undisturbed-process health baseline, **not** a transport failover/recovery exercise. The tool correctly reports `linker_namespace_acceptance=UNVERIFIED`, `independent_recovery=UNVERIFIED`, `injection_authorized=false`. Live execution stays NO-GO.
