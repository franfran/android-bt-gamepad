# RetroBox — Stage 3D D2b-2c: Isolated Remote `dlopen()`

## Purpose

This is an **actual ARM32 remote `dlopen()` experiment** restricted to a process forked by the test executable. It **does not** target or attach to Android's Bluetooth service. It does not change Bluetooth security, any system `.so`, or installed apps.

After D2b-2b demonstrated remote memory writes and restoration, this gate tests registers / ARM-vs-Thumb state / remote native function call / Android `dlopen()` and `/proc/PID/maps` validation.

## Usage (Mac)

```sh
unzip retrobox-stage3d-d2b2c-remote-dlopen-arm32.zip
cd retrobox-stage3d-d2b2c
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

Uploads the executable and add-on on **every run**, including after a reboot. No `/tmp` state or earlier D2a files are required.

### Positive acceptance (M3 output)

- `PTRACE_ATTACH OK`
- `PTRACE_GETREGS OK`
- `REMOTE CALL ARMED`
- `CHILD STOP signal=0x00000005`
- `REMOTE DLOPEN NONNULL`
- `ADDON MAPPED IN CHILD: YES`
- `PTRACE_DETACH OK`
- `CHILD CLEANUP DONE`
- `PASS: isolated remote dlopen and maps verification`

If the result is `FAIL`, paste the full output: the signal, register return value, and maps probe will help debug. **Do not interpret initial compilation as a verified pass.** The program has not been run on M3 by the author.

## Design and scope

- `fork()` owned child only; no command-line PID support.
- Parent and child share address-space layout after fork; the parent obtains `dlopen` and target string pointers and sets child ARM registers (`r0`, `r1`, `pc`, `lr`, `cpsr`) with `PTRACE_SETREGS`.
- On return, a deliberate ARM breakpoint halts the child so parent can inspect registers and `/proc/PID/maps`.
- Parent restores original register snapshot where possible, detaches, terminates **only its forked child**, and `wait4()` reaps it.
- No arbitrary process injection, Bluetooth function interception, auth change, or persistence.
- Fails closed: a non-SIGTRAP stop or missing `.so` mapping is not a pass.
- If the test shell is interrupted by an external kill/power loss, child process may persist until reboot; in normal operation it is cleaned up. This is an experimental ptrace PoC rather than a fault-tolerant injection framework.

**Important:** The test does not prove ability to inject a separate Android system process: that requires a different namespace, permissions, and recovery analysis.

## Cleanup

```sh
./cleanup-m3.sh 192.0.2.10:1080
```

Removes only `/data/local/tmp/retrobox_stage3d_d2b2c`. It does not change the existing `/data/local/tmp/retrobox_stage3d` directory or Bluetooth service.

## Build

The provided `remote_dlopen_fork` is a 32-bit ARM Android PIE, interpreter `/system/bin/linker`, and imports only system `libdl.so`. Its source uses direct Linux syscalls, so it requires no extra runtime dependencies. The original inert D2a `.so` has been bundled. There is no need to deploy `libdl_stub.c` or a stub `libdl.so`: those are not bundled and were used only for link-time ABI matching.
