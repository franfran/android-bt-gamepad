# RetroBox Stage 3D — S7-C1 isolated integrated loader

## Scope

This is an **isolated ARM32 engineering test**, not a Bluetooth injector. The executable accepts no target PID, uses `fork()` to create its own child, starts four worker threads, and only attaches to that child. The Bluetooth process and original `/system/lib/libbluetooth.so` are untouched.

**Important:** This is a newly compiled integration, **not yet tested on the M3**. Earlier S4/S5 passing does not mean this combined version will pass.

## What is new compared with S5?

1. Attach and save child leader registers.
2. Invoke an ARM32 raw `mmap2()` stub **in the child**, allocate 4096 bytes of child-private memory.
3. Use `PTRACE_POKEDATA`/`PEEKDATA` to copy and verify the `.so` path inside that private allocation. The path is **not** written into the child's existing stack.
4. Call `dlopen(path_in_child, RTLD_NOW)` in the child with a bounded wait and verify the library appears in `/proc/CHILD/maps`.
5. Invoke `munmap` in the child, restore original registers and detach; check four worker counters advance; kill and reap the owned test child.

Remote `dlopen` itself still uses the target thread's normal call stack for internal execution; this test only isolates the **path argument**. It is *not* proof of arbitrary-process stack safety, linker-lock safety or Bluetooth namespace acceptance. Timeout failure kills the **owned test child**; do not transplant this code into the Bluetooth process.

## Run (Mac, no NDK)

```bash
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

Expected key markers on a successful M3 run (not yet observed):

```
WORKERS READY=4
REMOTE MMAP2 OK: CHILD-PRIVATE SCRATCH
REMOTE CHILD SCRATCH PATH VERIFIED
REMOTE DLOPEN NONNULL
ADDON MAPPED IN CHILD: YES
REMOTE MUNMAP OK
REGISTERS RESTORED
PTRACE_DETACH OK
WORKERS PROGRESSED=4/4
PASS: isolated child-private mmap + remote dlopen + munmap + worker progress
```

`./cleanup-m3.sh 192.0.2.10:1080` deletes only this stage's uploaded test files; no automatic startup hooks are installed.

## Source and build notes

ARM32 PIE, interpreter `/system/bin/linker`, NEEDED `libdl.so`. Compiled using sandbox Clang/LLD with a temporary *link-time-only* stub defining the imported `dlopen`; that stub is **not** shipped. The runtime symbol resolves against M3's Bionic `libdl.so`.

Known limits: fork-shared function address assumption, single traced leader rather than all threads, simple worker contention (no linker locks), no Android target namespace test. **DO NOT run the obsolete Bluetooth injector `inject` mode.**
