# RetroBox Stage 3D — D2b-2d-A Bluetooth process attach/detach

## Scope

This is the first **real Bluetooth process** test. Unlike earlier fork-only tests, it briefly attaches to the **main thread** of `com.android.bluetooth`. **It does not inject an add-on**, invoke a remote function, or change registers, memory, authentication, files or system libraries.

It checks exact target process name (`/proc/<pid>/comm` must be `droid.bluetooth`) and dynamically discovers PID on each run, so it does not depend on previous boots. It uses `PTRACE_SEIZE` (no immediate stop), then `PTRACE_INTERRUPT`, `wait4`, and `PTRACE_DETACH`. It does not accept an arbitrary name; only a matching Bluetooth process is authorized. Only the leader thread is traced, not all worker threads.

**Warning:** Even a short interruption of Bluetooth's main thread could disrupt a live connection or cause unexpected timing problems. Run only when Bluetooth is idle and with physical access to the TV box. A root kernel or ROM may reject ptrace. This is experimental code, not a crash-proof debugger. A system reboot generally clears an ephemeral ptrace attachment; no auto-start or persistence is installed.

## Run from macOS

```bash
unzip retrobox-stage3d-d2b2d-a-bluetooth-attach-arm32.zip
cd retrobox-stage3d-d2b2d-a
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

Uploads its ARM32 static executable afresh each time. `/data/local/tmp` is merely a staging directory and does not need to survive reboot. Existing Stage 3D files are not read.

Expected PASS requires `TARGET COMM VERIFIED`, `PTRACE_SEIZE OK`, `PTRACE_INTERRUPT STOP CONFIRMED`, and `PTRACE_DETACH OK`, **plus** Bluetooth PID unchanged in the host post-check. If ptrace is denied or the main thread exits, stop and share the complete output; **do not retry rapidly**.

## Cleanup

```bash
./cleanup-m3.sh 192.0.2.10:1080
```

Removes only `/data/local/tmp/retrobox_stage3d_d2b2d_a`, not Bluetooth or any previous tests.

## Build

Source is freestanding C with Linux ARM EABI syscalls and no libc. Example clang build:

```bash
clang --target=armv7a-linux-gnueabi -fuse-ld=lld -nostdlib -static -Os -fno-stack-protector -Wl,-e,_start -o bt_attach_probe bt_attach_probe.c
```

Compile only, not yet tested on M3. This **does not establish** remote `dlopen()` compatibility with the Android Bluetooth linker namespace.
