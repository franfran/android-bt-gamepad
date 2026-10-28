# RetroBox Stage 3D — S4 (ARM32 prebuilt)

## S4 v2 fix

Fixed the ARM32 **raw `ptrace(PTRACE_PEEKDATA)` syscall ABI**: the read word is written through the fourth `data` argument, rather than returned in `r0`. S4 v1 passed a null data pointer, causing the read failure. This patch preserves all owned-child isolation and does not change the test scope.

## What is tested

This is an **isolated fork-owned child** test. The test binary does not accept any PID argument, does not attach `com.android.bluetooth`, does not call `dlopen`, and does not modify any system files or Bluetooth security settings.

Compared with S3, the scratch mapping is **created by code executing in the child**, using a remote ARM Linux `mmap2` syscall. It is `MAP_PRIVATE | MAP_ANONYMOUS`, **not** inherited/shared scratch memory. A separate preexisting `MAP_SHARED` page is used solely to monitor thread progress.

The harness:

1. Starts one owned child and four worker threads; seizes and interrupts the child leader.
2. Executes a remote **child-side** `mmap2` to reserve three inaccessible pages.
3. Executes remote `mprotect` to enable only the middle page.
4. Uses `PTRACE_POKEDATA` / `PTRACE_PEEKDATA` to initialize and inspect the middle-page payload and canaries.
5. Executes a stackless remote function to mutate payload `35` to `42`, verifies canaries.
6. Runs a deliberately non-returning test function, confirms a 250 ms timeout, interrupts and restores registers, and rechecks the child-private payload.
7. Executes remote `munmap`, detaches, confirms all four workers progress, and reaps the child.

**Limitations:** Not tested on M3 yet. Memory restoration is verified only for this controlled test function. This does not prove that Android's linker lock or real `dlopen` can be safely interrupted. This uses pre-existing, child-owned ARM code for syscalls, not injected instructions. The test does not actively read `/proc/PID/maps` to confirm deallocation; it checks a zero return from child `munmap`.

## Run on macOS (no Android NDK needed)

```sh
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

Each run uploads the binary, and no file from a previous boot is required. Optional cleanup:

```sh
./cleanup-m3.sh 192.0.2.10:1080
```

Static ELF ARM EABI, compiled with Clang/LLD without an Android NDK. `source`: `safety_s4.c`.
