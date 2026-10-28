# RetroBox Stage 3D — S5 isolated multi-thread remote `dlopen`

## Goal and scope

S1–S4 passed on the M3. D2b-2c separately passed isolated `dlopen` on a single-thread fork-owned child. S5 combines the two capabilities: it creates its **own forked child**, starts four worker threads, uses `ptrace` on the **owned child leader only**, invokes `dlopen` in that child, verifies that the inert add-on was mapped, restores registers, detaches, observes worker progress and reaps the owned child.

**This is not Bluetooth injection.** There is no arbitrary PID argument. The test never discovers, attaches or modifies `com.android.bluetooth`.

## Run from macOS

```sh
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

No Android NDK. Both ELF files are pushed on every run to `/data/local/tmp/retrobox_stage3d_s5/`. Neither depends on previous boots.

Expected important markers (not yet verified on M3): `WORKERS READY=4`, `REMOTE DLOPEN NONNULL`, `ADDON MAPPED IN CHILD: YES`, `PTRACE_DETACH OK`, `WORKERS PROGRESSED=4/4`, `PASS`.

Clean up files only with `./cleanup-m3.sh 192.0.2.10:1080`.

## Engineering notes

- Uses M3's Android `/system/bin/linker` and `libdl.so`; a **link-time-only stub** was used to resolve the ELF dependency while building. The stub is **not shipped** or loaded on M3.
- Owned-child caller and callee share `dlopen` address following `fork`. This assumption does **not** hold for an independently spawned Bluetooth process.
- The child contains four worker threads doing only simple counters/sleeps, not concurrently calling dynamic linker functions. This is a concurrency smoke test, **not** a linker-lock stress test.
- The remote-call wait is bounded to 3 seconds and on timeout the test terminates its own child, not the Bluetooth service. Recovery of an arbitrary production process from linker deadlock is **not** demonstrated.
- `PTRACE_ATTACH` stop is bounded by polling. There is a separate 12-second overall timeout if your Mac provides `timeout`; otherwise rely on internal remote-call bound and report if stalled.
- This source is intended for ARM32 / Android 12. The compiled ARM32 ELF was statically inspected, **not** executed against the M3 in this environment.
- Never run the old D2b-2d-B `inject` command: it still has unsafe stack scratch and linker deadlock handling.

## Next decision

If S5 passes, the isolated prerequisites are established. The remaining blocker is **production Bluetooth injection safety** (multi-thread linker-state consistency, thread selection, namespace restrictions and deterministic recovery). A PASS here does **not** authorize injecting a 48-thread system Bluetooth process.
