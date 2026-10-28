# RetroBox Stage 3D D2b-2b — remote memory prerequisite

## Scope and honest status

This is a **prerequisite** for an isolated remote `dlopen()` experiment, not remote `dlopen()` itself.

The ARM32 static ELF makes a child with `fork()`, pauses the child, performs `PTRACE_ATTACH`, `PTRACE_PEEKDATA`, `PTRACE_POKEDATA`, checks the new value, restores the original value, detaches, and kills/reaps the child. No arbitrary target PID is accepted; it never touches Bluetooth, the Android Bluetooth library or the controller. It has no dependencies on an older stage's binaries or `/tmp` state.

## Run on Mac with M3 connected over ADB

```sh
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

The script pushes the binary afresh on every run to `/data/local/tmp/retrobox_stage3d_d2b2b/`, so a reboot doesn't matter. Expected success output contains:

```
PTRACE_ATTACH/WAIT OK
REMOTE PEEKDATA OK marker=0x52425831
REMOTE POKEDATA OK
REMOTE VERIFY OK marker=0x52425832
RESTORE VERIFIED
PTRACE_DETACH OK
CHILD CLEANUP OK
PASS: remote read/write/restore on forked child only
```

If a step fails, report the full output. This prototype makes no claims about remote `dlopen`, target process linker namespace, or production hooking. It was cross-compiled and structurally inspected in a sandbox but **not yet tested on an M3**.

## Cleanup

```sh
./cleanup-m3.sh 192.0.2.10:1080
```

## Next after PASS

To prove true remote `dlopen`, prepare a dedicated test target process with its own Android Bionic linker, and test saving/restoring registers, remote function invocation, return/trap handling, and library load/unload **only in the test target**, prior to any Bluetooth-process experiment. The target must never be a system service in this phase.

## Build

```sh
clang --target=armv7a-linux-gnueabi -fuse-ld=lld -Oz -fno-stack-protector -fno-pic -nostdlib -static -Wl,-e,_start -Wl,--build-id=none -o ptrace_memory_probe ptrace_memory_probe.c
```

Copyright (c) RetroBox contributors. SPDX-License-Identifier: MIT.
