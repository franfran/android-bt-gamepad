# RetroBox Stage 3D — S3 Isolated Scratch Memory Safety Harness

**Prebuilt ARM32 EABI5 static binary. No Mac Android NDK required.** Built with Clang + LLD in the assistant sandbox. Not yet run on iMETBOX M3 hardware.

## Run on Mac

```bash
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

The script re-uploads the executable on every run. It does not rely on files from prior boots.

## What this proves

- An owned fork child containing 4 worker threads can be briefly controlled with `PTRACE_SEIZE` and `PTRACE_INTERRUPT`.
- A distinct 3-page `MAP_SHARED` allocation acts as scratch memory. Only its middle page is writable; first and last pages remain `PROT_NONE`.
- Two canary words surround a payload inside scratch. A synthetic stack-free ARM remote call changes the payload from 35 to 42, then returns to a trap. Parent verifies the payload, the canaries, the untouched sentinel, and original register restoration.
- A synthetic tight-loop remote call is interrupted after a 250ms timeout, followed by register restoration and scratch-integrity check.
- After detach, 4/4 child workers continue; child is killed/reaped by parent.

**Limitations:** The memory is deliberately `MAP_SHARED` between our parent and owned child, not allocated by remote `mmap()` inside a pre-existing target. The guard page setup only protects adjacent *virtual pages* and does not guarantee safety of arbitrary library calls. The synthetic remote function does not use the stack, external linker, locks, or `dlopen`; timeout interrupt + register restoration cannot safely unwind arbitrary `dlopen()` side effects. This is not clearance to use the older Bluetooth `inject` mode. A parent crash can still bypass the in-process cleanup watchdog.

## Build reference (not required on Mac)

```bash
clang --target=armv7a-linux-gnueabi -marm -march=armv7-a -O2 -nostdlib -static -ffreestanding -fno-stack-protector -fno-pie -Wl,-no-pie -fuse-ld=lld -Wl,-e,_start -Wl,--build-id=none safety_s3.c -o safety_s3_arm32
```
