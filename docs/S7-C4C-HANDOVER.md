# S7-C4C — Bluetooth process execution loader: detailed handover

**Status (2026-10-28):** S7-C4C-1/2 independently started ARM32 **test-target loader PASS on M3** (PR #3). Actual Bluetooth-specific execution loader and independent recovery are NOT implemented; live Bluetooth injection remains NO-GO. This file is the continuation entry point for a new conversation/agent.

## Objective

Load the tiny *inert* `libretrobox_ds3_addon.so` once into the already-running `com.android.bluetooth` process on an owner-controlled rooted Android 12 ARM32 iMETBOX M3, without modifying `/system/lib/libbluetooth.so`, global security rules or persistent boot configuration. This **does not yet fix DS3 bonding**. Follow-up D3 would attach observation-only hooks, then consider scoped DS3 policy only after identifying the failure branch.

## Verified building blocks and where to find them

| Building block | Source | Verification |
|---|---|---|
| ARM32 isolated attach, regs, memory | `experiments/stage3d-ptrace/`, `stage3d-memory/` | M3 PASS |
| Isolated remote `dlopen` | `experiments/stage3d-isolated-dlopen/` | M3 PASS |
| Target-owned scratch + remote `mmap2/mprotect/munmap` | `experiments/s4/safety_s4.c` | M3 S4 v2 PASS |
| Multi-thread isolated `dlopen` | `experiments/s5/s5_multithread_dlopen.c` | M3 PASS |
| Integrated child private path → `dlopen` → `munmap` | `experiments/s7-c1/s7c1_isolated_loader.c` | M3 PASS, fork-owned only |
| Dynamic target ELF / Thumb function pointer | `experiments/s7-c3-resolver/s7c3.py` | M3 v3 PASS |
| Strict service identity and add-on checksum | `experiments/s7-c4b/s7c4b.py`, `stage.py` | M3 read-only PASS |
| Constructor hang / concurrent `dlopen` handling | `experiments/s7-c3d/`, `s7-c3e/` | M3 PASS only in owned test processes |
| Policy/quarantine simulator | `experiments/s7-c3-recovery/` | Host unit tests, not target recovery |

## Latest real target state (do NOT hardcode)

Evidence from S7-C4B: PID `671`, 49 threads, UID 1002, tracer 0, staged add-on hash `079b177fdb90fc4ed2b6ac727925263aef1615b0808cd72d4268b95e5e90197a`, `addon.mapped=false`, `inspection_issues=[]`. Resolved `dlopen` Thumb pointer was `0xf326e851` **for that snapshot only**; must recompute on every run. Stage C4A uses `/data/local/tmp/retrobox_s7c4_inert/libretrobox_ds3_addon.so` and has verified identical bytes.

## Unsolved problems, in priority order

1. **Return/trampoline:** S7-C1 uses a return site within fork-owned child. Existing Bluetooth service does not share that address. Define a valid ARM32 Thumb-safe return mechanism that remains inside controlled scratch, preserves CPU state, signal masks and stack alignment, and can be removed without leaving executable memory behind. Test independently before live use. Avoid `LR=0` or deliberately faulting in production service.
2. **Target scratch lifecycle:** allocate target-private memory using a known-safe remote syscall/call, protect guard pages, verify writes/reads, place argument path there, and release on successful call. Never `SP+256` or overwrite target original stack. An actual `dlopen` still uses ordinary thread call stack internally; argument isolation does not solve all risks.
3. **Thread/linker concurrency:** 48–49 live Bluetooth threads. S7-C3e showed independent `dlopen(B)` can complete while constructor `A` is running, but did not prove absence of internal linker locks. Stopping all threads can itself deadlock if a stopped thread holds a linker lock. A simple timeout cannot safely unwind a half-entered linker. Decide and document risk policy; do not imply reliable rollback of arbitrary stuck linker calls.
4. **Linker namespace acceptance:** symbol/ELF address verification and staging do not prove Bluetooth can `dlopen` `/data/local/tmp`. Android 12 namespace may reject it. Preserve exact `dlerror()` capture design, no alternate unchecked arbitrary file path, and no global linker policy weakening.
5. **Failure/recovery:** define explicit states before and after entering `dlopen`; differentiate safe pre-call abort from **post-call indeterminate quarantine**. Validate independent recovery access and operator-controlled service restart path. No automatic retry and no production auto-start.
6. **Observation-only stage:** once inert load itself is verified, separately build passive native instrumentation for DS3 address/PSM to identify whether failure occurs before security approval, in HCI auth, or at Java HID Host. No global authentication bypass.

## Engineering gates and acceptance

- **C4C-1: implementation review:** target-only loader source compile, no arbitrary PID/user-supplied library path, dynamic UID/process/ELF digest check, no unsafe stack scratch, no `LR=0`, no unbounded wait. Source-level unit tests for address/snapshot races.
- **C4C-2: owned-process parity:** new trampoline / register+scratch lifecycle tested in an **independently started non-fork-owned** Android test process (important because fork-address sharing is removed). Include normal exit, `dlopen` error, concurrent threads, signal handling, no stale attach, cleanup and timeout policy.
- **C4C-3: operator-reviewed hazard assessment:** show namespace evidence and explicit recovery plan. Default NO-GO remains until reviewed; do not fabricate a proof that can't be obtained without live execution.
- **C4C-4: owner-initiated single target trial, only if approved:** inert add-on mapped in live Bluetooth `/proc/PID/maps`, Bluetooth remains usable, no repeat attempts on failure, service status verified and evidence recorded. No hooks or DS3 auth changes in this gate.
- **D3 follows separately:** targeted passive hooks, then a security-scoped DS3 USB-enrollment design and Android input verification.

## Why this is not solved by BlueZ/Sixaxis drop-in

BlueZ works through Linux's own Bluetooth management path. M3 owns the controller through Android HAL/UART and a legacy Fluoride stack, with no public kernel hci0. BthPS3 is a Windows driver. Ideas are transferable, stack implementation and privilege boundaries are not.

## Working constraints

Mac lacks Android NDK. Sandboxed prebuilt ARM32 artifacts have been used; include reproducible Clang/LLD build recipes when possible. `su 0` works (`su -c` doesn't). ADB serial must be supplied explicitly. Store PRs/reviews in GitHub so context survives chat resets.

## Latest test-target breakthrough: S7-C4C-1/2 (M3 measured, 2026-10-28)

Code: `experiments/s7-c4c/` in [PR #3](https://github.com/franfran/android-bt-gamepad/pull/3). Unlike S7-C1, tracer and 48-worker target are started as separate processes, with a persistent ADB session keeping the target alive. The target writes its own PID; controller dynamically resolves target ELF symbol RVAs using its `/proc/PID/maps` mapping. Tested on M3: target-private `mmap2` (4 pages: guard/RW/RX/guard), executable return-trampoline protection and validation, missing module `dlopen` → NULL + nonempty `dlerror`, successful inert module `dlopen` and mapping, scratch canaries, background worker progression, remote `munmap`, test-only process cleanup. Operator terminal ended `S7-C4C-1/2 INDEPENDENT TARGET = PASS (NOT Bluetooth authorization)`.

**Critical limitation:** The very first remote call returns through `rbxc4c_return_trap`, specially compiled into the test target. Later remote calls use a target-private RX return trampoline. Actual `com.android.bluetooth` has **no built-in test trap**. A target-independent, ARM/Thumb-safe bootstrap plus independently verified service recovery/namespace behavior is still required. No remote `dlopen` was performed on Bluetooth. This is a real target-specific parity milestone, not proof of safe production injection.

Next work: investigate a **target-independent bootstrap** in a similarly independently started non-Bluetooth test process (without its precompiled return-trap), then separately assess linker namespace and an out-of-band service recovery procedure; avoid claiming register restoration unblocks a stuck linker. Do not reuse the retired `bt_inert_inject` tool.

## Continuation after PR #3: ARM SVC bootstrap candidate (now M3 normal-path measured)

A separate stacked experimental branch `feat/s7-c4c-svc-bootstrap-test`
removes controller dependence on the test target's precompiled BKPT return
address for its first remote syscall. It selects a verified ARM `svc #0`
instruction in the standalone test ELF, uses tagged `ptrace` syscall stops
for remote `mmap2/mprotect/munmap`, and keeps the private RX BKPT trampoline
for test-only remote `dlopen` return. The original target still includes
unused test helper symbols; this is a controller independence test, **not**
proof of arbitrary real-service injection.

**Status: normal-path M3 test PASS on 2026-10-28; CI 18/18 PASS.**
Signal/forced-timeout fault injection and independent recovery remain untested.
This is partial owned-process parity, not completion of all C4C-2 gates.
Independent recovery and namespace acceptance are separate gates; production Bluetooth stays NO-GO.

## PR #4 closeout: SVC bootstrap normal-path PASS on M3 (2026-10-28)

The continuation branch is now [draft PR #4](https://github.com/franfran/android-bt-gamepad/pull/4)
stacked on PR #3. In the separately started **test-only** `rbxc4c_target`,
the controller selects an ARM-state `svc #0` within the target's own
executable mapping, uses tagged `PTRACE_SYSCALL` stops for remote
`mmap2/mprotect/munmap`, and uses an RX private return trampoline for its
test `dlopen/dlerror` wrapper calls. Unlike PR #3, the controller does not
use a precompiled `rbxc4c_return_trap` for initial allocation. The legacy
helper code is still built into the test ELF and `dlopen` remains an exported
test-target wrapper; the result is **not a general-process call loader**.

**Measured M3 PASS:** owner returned the complete run output: PID 2963,
48 workers, dynamically resolved load bias, SVC bootstrap chosen, target
private mmap2, RX return trampoline, expected negative library load and
nonempty `dlerror`, inert module mapped, scratch canaries intact,
background worker progression, SVC-driven munmap, scoped test-only cleanup.
CI for the corrected artifact ran 18/18 host tests PASS (Actions
`40802426406`, artifact `12865984164`). PID/address are observation-only,
never configuration values. See `docs/STATUS.md` for the exact selected
stdout lines.

**Next safety work before any promotion:** do isolated, deliberate
unexpected-signal and post-entry timeout tests with unambiguous
quarantine/no-retry evidence; evaluate whether register restoration and
signal-delivery stops are correctly distinguished; prepare an independently
verifiable, operator-controlled recovery plan. Do not assume target-thread
linker lock safety. Verify Bluetooth's linker namespace without executing
an unchecked library in the live process. Owner review is required for
future safety gates, and **live Bluetooth remains NO-GO**. No automated
production injection, no global Bluetooth auth policy changes.

## PR #5 fault-path qualification (M3 PASS for both fixed test modes)

A further **test-only** stacked branch `feat/s7-c4c-fault-path-test`
adds two separate fixed controller variants using the PR #4 independent
test target. `--fault-case signal` requests an expected SIGUSR1 delivery
stop from a compiled test helper; `--fault-case timeout` enters a compiled
nonreturning loop and checks the bounded wait. Both must classify an
interrupted remote call as `QUARANTINE`, must never retry/resume it, and
must request SIGKILL only for the verified, owned test target. The normal
PR #4 branch remains intact.

This intentionally tests **classification and scoped termination only**,
not restoration of a hung Bionic linker, not a clean service restart, and
not Android Bluetooth linker namespace acceptance. Owner-operated M3 evidence now supports both fixed classifications; this
remains distinct from any proof of real linker/service recovery. Live Bluetooth
continues NO-GO.

**Source/CI qualified (PR #5):** Actions `40803809282` built three ARM32
controllers and ran **23/23 host tests PASS**; artifact `12867485949`
includes the runner and both fixed fault-mode binaries. General source
safety workflow `40803809204` PASS. **Both M3 test-only fault modes passed (2026-10-28); see the measured
closeout below.**

## PR #5 M3 closeout — signal and timeout quarantine (2026-10-28)

From artifact `12867485949` (Actions run `40803809282`), owner executed
the signal and timeout fixed-mode controllers **separately** on M3 using
the same independent 48-worker test-target runner. The two runs reported:

- **Signal:** PID snapshot 3129, ASLR base `0x0dfe7000`, ARM SVC
  bootstrap selected, private mmap/trampoline setup PASS, expected
  `SIGUSR1 DELIVERY STOP REJECTED; NO RESUME OR RETRY`, followed by
  `STATE=QUARANTINE; SAFE_TO_RETRY=false`, scoped test kill requested,
  and `TEST-ONLY CLEANUP COMPLETE`.
- **Timeout:** PID snapshot 3255, ASLR base `0x09ea5000`, same bootstrap/
  trampoline setup, expected `NONRETURNING TEST CALL QUARANTINED; NO
  RESUME OR RETRY`, followed by the same quarantine, scoped test kill
  request and confirmed runner cleanup.

See `docs/STATUS.md` for the actual selected output lines. CI for these
variants: **23/23 host tests PASS**. Both tests were deliberately scoped to
compiled functions in an owned `rbxc4c_target`; **neither entered
`dlopen`**. Thus C4C-2's *representative abnormal-call classification*
in this isolated target is evidenced, but the wider multithread/linker risk
and recoverability obligations remain unproven. Do **not** infer that
register restoration, SIGKILL, or Android service restart can unwind a
partially entered linker operation.

**Next engineering gate: C4C-3 evidence + operator hazard review.** Propose
read-only, dynamically refreshed Bluetooth identity/mapping/namespace
evidence; separately document independent USB/ADB control, operator
restart/recovery playbook, abort thresholds, and test/production
differences. No automatic service termination or live injection.
Only after an explicit owner-reviewed GO/NO-GO assessment may any further
production experiment be considered. Keep PR #5 as reviewable test-only
evidence; it is not a production authorization.

## C4C-3 formal safety gate (2026-10-28)

See [S7-C4C-3-HAZARD-ASSESSMENT.md](S7-C4C-3-HAZARD-ASSESSMENT.md) and [Issue #6](https://github.com/franfran/android-bt-gamepad/issues/6). Read-only risk matrix, missing namespace evidence, thread/linker concurrency hazards, independent wired recovery requirements and explicit no-go conditions are documented. **NO-GO is the current decision**, not a statement that an M3 production trial failed. No service restart or Bluetooth injection has been executed for this review. Future evidence must be refreshed and classified as measured/inferred/unverified.
