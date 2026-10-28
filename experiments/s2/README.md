# RetroBox Stage 3D — Safety Harness S2

ARM32 EABI5 statically linked executable, cross-compiled using Clang/LLD in the assistant environment; Mac Android NDK NOT needed. Not yet tested on iMETBOX M3 hardware.

Run:

```sh
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

Safety scope: only the fork-owned child created by this executable; no external PID arguments; does not attach Bluetooth or alter authentication. Re-uploads executable every time, no reliance on reboot-persistent /tmp files.

Design: fork child with four clone-created worker threads using `MAP_SHARED` ticks. Parent traces child leader via `PTRACE_SEIZE`, stops with `PTRACE_INTERRUPT`, snapshots ARM r0-r15/CPSR/orig_r0. For positive case, sets PC to a stack-free ARM function which adds seven to r0 and returns via LR into an ARM BKPT trap, checks SIGTRAP and result 42. For negative case, calls a stack-free infinite loop and confirms 250ms timeout, then interrupts and restores registers while stopped. Verifies registers by reading them back. Detaches, verifies all four worker ticks advanced, kills/reaps **owned child**.

Expected key lines (only if M3 passes):

```
WORKERS READY=4
PTRACE_SEIZE OK
PTRACE_INTERRUPT STOP OK
PTRACE_GETREGS OK
REMOTE FUNCTION RETURN OK r0=42
REGISTERS RESTORED AND VERIFIED
REMOTE CALL TIMEOUT CONFIRMED (250ms)
TIMEOUT CHILD INTERRUPTED OK
REGISTERS RESTORED AND VERIFIED
PTRACE_DETACH OK
WORKERS PROGRESSED=4/4
PASS: isolated bounded remote call + timeout interrupt + register restore
CLEANUP: OWNED CHILD REAPED
```

Limitations: remote call is a synthetic stack-free ARM function, not `dlopen`, is made only on fork-owned process, and does not validate arbitrary multithreaded loader locks or safe abort of arbitrary functions. Interrupting a live `dlopen` is not a safe generic rollback. S3 will still need scratch memory, thread/lock safety and error recovery before considering Bluetooth injection. The watchdog is implemented in process using monotonic clock + WNOHANG, not an independent supervisor; a fatal bug in the parent could bypass it. Executing ptrace even on an owned child can fail or crash; test only when M3 can be accessed physically.

Rebuild (developer only):
```sh
clang --target=armv7a-linux-gnueabi -marm -march=armv7-a -O2 -nostdlib -static -ffreestanding -fno-stack-protector -fno-pie -Wl,-no-pie -fuse-ld=lld -Wl,-e,_start -Wl,--build-id=none safety_s2.c -o safety_s2_arm32
```
