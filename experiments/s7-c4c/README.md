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

## S7-C4C v2 startup diagnostics

The first M3 run stopped at the runner's **identity gate**:
`FAIL CLOSED: independently started target identity mismatch`.
No remote `dlopen` was attempted. The original runner removed the test directory
before reporting `/proc` or `target.log`, so this output alone cannot establish
whether the shell-background PID differed from the actual process, the target
failed to execute, or the 48 worker threads failed to start.

v2 launches via a background `sh -c 'exec ...'` wrapper, waits for a strictly
validated and ready target (bounded), and cross-checks `pidof` against the
pidfile. It validates UID 0, exact `/proc/PID/exe`, `/proc/PID/cmdline`,
`/proc/PID/comm`, tracer and >=49 threads. On mismatch it **prints** the
observed PID, comm, cmdline, executable, UID, state, thread count and startup
`target.log` before cleanup, without attaching. Target source also logs basic
startup and clone failures. No Bluetooth process or system library is touched.

If v2 still fails, share the complete `STARTUP DIAGNOSTICS` section: it will
identify the next concrete correction without blind retries.

## Measured vs unmeasured

- **Compiled locally:** target, controller, test .so; ELF32 ARM PIE verified.
- **Host unit tests:** run locally and in CI.
- **M3 run:** v1 preflight FAIL CLOSED at identity validation; v2 untested. Do not claim M3 PASS before operator shares output.
- **Live Bluetooth process:** not touched; `injection_authorized=false`.

## Cautions / limitations

- `dlopen` naturally uses the target leader's ordinary stack; **no path or trampoline scratch is written to that stack**. Remote function calls cannot be made zero-risk simply by moving argument storage off stack.
- Bionic linker may accept libraries in the test shell namespace yet reject `/data/local/tmp` from the Bluetooth namespace.
- `ptrace` stop, signal delivery, TLS and linker locks may behave differently in a full Android service. There is no safe register-only rollback after entering linker. Stalling can force a scoped **test-target** kill, but production process recovery is unproven.
- Device connection loss can prevent cleanup. Use `adb` to inspect target process and remove only the fixed test directory; never use an unvalidated PID from stale files.