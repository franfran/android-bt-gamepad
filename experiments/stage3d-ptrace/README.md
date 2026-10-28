# RetroBox Stage 3D — D2b-2a isolated ptrace probe

## Scope

A self-contained ARM32 executable (ELF EABI5, statically linked, no NDK runtime) that uses Linux system calls to:
1. `fork()` its **own** short-lived child, which blocks in `pause()`;
2. attach that child with `ptrace(PTRACE_ATTACH)`;
3. use `wait4()` to confirm the child entered a traced stop;
4. `ptrace(PTRACE_DETACH)`;
5. terminate/reap the child with `kill()`/`wait4()`.

**No target PID argument is accepted. This never attaches to `com.android.bluetooth` or other existing processes.** The only observable effect should be its own child process lifecycle. It does not load a plugin or modify the device's Bluetooth stack. This is *D2b-2a*, not D2b-2b/c.

## Run

```bash
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

Expected success lines include `PTRACE_ATTACH OK`, `CHILD STOP CONFIRMED`, `PTRACE_DETACH OK`, and `PASS`. An `errno` failure indicates the M3's process-tracing behavior needs investigation; do not proceed to injection.

The wrapper invokes `/system/bin/timeout 10` to avoid hanging indefinitely. If that utility is unavailable, execute directly:

```bash
adb -s 192.0.2.10:1080 shell su 0 /data/local/tmp/retrobox_stage3d_d2b2/ptrace_child_probe
```

The cleanup script removes the probe binary, not Stage D2a files. In normal execution the probe kills/reaps its child itself. If a failure is interrupted before cleanup, investigate any residual `ptrace_child_probe` process **before** terminating it; do not use broad `pkill` commands.

## Compilation and validation

Compiled in a Linux sandbox with LLVM Clang for `armv7a-linux-gnueabi`, `-nostdlib -static`. ELF format inspected with `file`. **Not yet run on M3**. It does not use Android NDK or libc.

## Risks and decision gate

A controlled `ptrace` attach to a child still suspends that child briefly. Do not run on a production device if it is performing critical operations. D2b-2a passing proves nothing about injecting `dlopen()` into the Bluetooth process, resolving linker namespaces, intercepting security calls, or DS3 wireless pairing. Those are separate gates with their own safeguards.
