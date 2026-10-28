# S7-C4C-1/2 — independent ARM32 process execution parity

## What this delivers

The tracer and the target are **two independently launched ELF32 ARM processes**. The tracer **does not fork the target**. It only recognizes the dedicated `rbxc4c_target` by process name, executable command line, UID=0 and >=49 threads. It gets PID from a fixed test-only pidfile; it does not accept arbitrary target PIDs or library paths. It cannot target `com.android.bluetooth`.

1. Resolve bootstrap symbols using the target ELF's exported symbol RVAs plus a separately calculated target `/proc/<pid>/maps` load bias (ASLR aware, no fork-relative pointers).
2. Attach the target leader with `ptrace`, saving and checking ARM registers and 8-byte SP alignment.
3. Bootstrap target-owned `mmap2()` through the target-image `BKPT` return point. Reserve four pages: `PROT_NONE | RW | RX | PROT_NONE`.
4. Write a two-instruction **ARM-state** return trampoline into the private mapping, verify it, then `mprotect` it RX (no RWX mapping).
5. Invoke test-target `dlopen()` via the **new target-owned trampoline** and test both an intentionally missing `.so` (NULL + nonempty `dlerror`) and a tiny inert test `.so` (nonnull + `/proc/maps` proof).
6. Verify scratch canaries and background worker ticks, unmap using the target-image return trap (not the trampoline that's being unmapped!), restore registers, then detach.
7. On any indeterminate call, **terminate this owned test process**, not detach/resume/retry it. External runner performs a separate test-name check before cleanup.

This is real independent-process ptrace testing, **not** a demonstration of safe Bluetooth injection. Bootstrap relies on special symbols deliberately compiled into `rbxc4c_target`; the production Bluetooth service has no such symbols. A validated, target-independent bootstrap and service recovery remain unresolved. This also does not prove Bluetooth linker namespace accepts the staged add-on.

## Run on M3 (prebuilt included)

```bash
python3 run-on-m3.py YOUR_ADB_SERIAL
```

The script uploads three prebuilts (ARM32), independently launches the target with 48 worker threads via `su 0`, runs controller, and kills/removes **only its fixed, identified test target**. No Android NDK required on Mac. The fixed remote staging directory is `/data/local/tmp/retrobox_s7c4c_test`. Do **not** re-target this code to Bluetooth.

## Build and verify

```bash
./build-sandbox.sh
python3 -m unittest discover -s tests -v
```

Clang / LLD / Python3 / `readelf` required for rebuilding in Linux CI or sandbox. Build produces `target_offsets.h` from exported ELF symbols. The linker stub is a compile-time shim **not shipped**. Target runtime imports the M3's actual Bionic `libdl.so`.

## M3 startup evidence and v3 correction

- **v1:** `FAIL CLOSED: independently started target identity mismatch`.
- **v2 (actual M3):** `target.log` contains `TARGET STARTED`,
  `TARGET PR_SET_NAME OK`, `TARGET 48 WORKERS SPAWNED`, but the shell
  background PID was already gone and `pidof rbxc4c_target` found no process.
  **Measured:** target executed through worker spawning, then disappeared.
  **Hypothesis, NOT confirmed:** Android `su` / shell / ADB job-lifecycle
  cleanup terminated the background descendant when the shell command ended.

**v3:** `run-on-m3.py` now keeps a separate, foreground `adb exec-out su 0
sh -c 'exec rbxc4c_target ...'` session alive throughout the independent
ARM32 controller execution. This is independently started **from the tracer**:
the controller does not fork or own its target. The actual target calls ARM32
`getpid()` and writes the fixed `target.pid` itself. The runner does not infer
PID from `$!` or use a detached shell background job. It confirms the persistent
ADB session, validates UID, `/proc` identity and 49+ threads, and rejects an
already-running target rather than killing it. Test-only cleanup is scoped
and revalidates target identity before any kill; startup failures retain
`target.log` for reporting.

**Tested so far:** local ARM32 ELF32 PIE cross-compile, 16 host contract/mock
tests. **v3 has NOT YET passed an M3 trial**. Normal `dlopen`, trampoline
and actual M3 cleanup must be verified before advancing the gate.

The runner now shows controller stdout even if controller returns a nonzero
exit code, so linker/ptrace failures are visible rather than being swallowed.

## Measured vs unmeasured

- **Compiled locally:** target, controller, test .so; ELF32 ARM PIE verified.
- **Host unit tests:** 16 PASS locally; CI is a separate build check.
- **M3 run:** v1/v2 FAILED CLOSED before ptrace; v3 pending.
- **Live Bluetooth process:** never touched; injection remains NO-GO.

## Cautions / limitations

- `dlopen` naturally uses the target leader's ordinary stack; **no path or trampoline scratch is written to that stack**. Remote function calls cannot be made zero-risk simply by moving argument storage off stack.
- Bionic linker may accept libraries in the test shell namespace yet reject `/data/local/tmp` from the Bluetooth namespace.
- `ptrace` stop, signal delivery, TLS and linker locks may behave differently in a full Android service. There is no safe register-only rollback after entering linker. Stalling can force a scoped **test-target** kill, but production process recovery is unproven.
- Device connection loss can prevent cleanup. Use `adb` to inspect target process and remove only the fixed test directory; never use an unvalidated PID from stale files.
## M3 v3 acceptance (measured 2026-10-28)

**M3 PASS**: operator verified independent foreground ADB target session alive, 48 workers ready, load-bias resolution, target-private remote `mmap2`, RX return trampoline, negative `dlopen` + `dlerror`, inert module mapped, canaries intact, workers progressed, remote `munmap`, return via test-target image bootstrap and test-only cleanup. The target was independently launched, not forked by tracer. See `docs/STATUS.md` for exact measured assertions. Earlier v1/v2 startup gating failures are superseded by this v3 result.

**Scope guard:** the initial BKPT bootstrap is built into this test target. Bluetooth has no matching test stub. M3 PASS does **not** authorize real Bluetooth injection, prove its linker namespace, guarantee safe rollback, or repair DS3 wireless pairing.
