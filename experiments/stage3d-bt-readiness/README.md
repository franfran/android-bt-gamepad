# RetroBox Stage 3D D2b-2d-B — linker preflight v2

This read-only diagnostic resolves the prior `FAIL: cannot locate libdl.so image mapping` by checking what is **actually mapped** in the target process, rather than assuming that `libdl.so` is a separately mapped ELF. On Android, `dlopen` may be provided via a forwarding stub and handled by the Bionic dynamic linker; symbol address identity must be verified before any remote call.

## Run on Mac

```bash
chmod +x run-on-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

It collects process state, relevant maps, linker paths, and rechecks the PID. The report is saved as `d2b-2d-b-linker-preflight.txt` alongside this script.

**Do NOT run the previous bundle's `inject` mode.** The previous injector has not been validated for a multithreaded Android Bluetooth process: using stack space above SP, waiting indefinitely during remote `dlopen`, not accounting for remote linker symbol implementation, and failing to guarantee restoration after an unexpected stop may harm the service. A fresh safe injector needs a deliberately designed remote scratch region, timeouts, and restore recovery. This test does not perform ptrace, injection, or system modifications.

Files required on M3 before running: **none**. Requires ADB connected and `su 0` functioning. No reboot dependency.
