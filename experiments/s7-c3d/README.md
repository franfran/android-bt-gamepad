# RetroBox Stage 3D — S7-C3d: isolated constructor-stall / fail-closed test

## Scope

ARM32 test for M3 Android 12. **No Bluetooth process interaction, no arbitrary PID, no ptrace, no remote dlopen, no system file changes, no auto-start.** A fork-owned child with four syscall-only worker threads calls `dlopen()` on two deliberately slow `.so` files. Their constructors create a marker and sleep. The parent detects the constructor's entry and checks a bounded deadline.

- Scenario 1: constructor delay ~450 ms; expect normal `dlopen` completion under 1800 ms.
- Scenario 2: constructor delay ~3500 ms; expect a 300 ms deadline to expire, then **QUARANTINE / SAFE_TO_RETRY=false**. Parent kills **only its owned child** and reaps it; it does not pretend that interrupting real `dlopen` or merely restoring registers repairs linker state.
- Four worker threads should keep progressing while the constructor runs.

**Important limitation:** this is a real `dlopen` constructor-delay exercise, but it does **not** prove the Bionic global linker mutex is held by another thread, nor test true concurrent `dlopen` lock contention. It is a failure-policy integration smoke test. Bluetooth injection remains NO-GO.

## Running on macOS (no NDK)

```sh
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

The runner reuploads all three files on each run. No previous `/tmp` state is required. Use `./cleanup-m3.sh 192.0.2.10:1080` to remove only this package's files after testing; not mandatory.

Expected final line: `PASS: constructor-stall detection and fail-closed policy`.

If test fails, **do not run any earlier Bluetooth `inject` mode**. Report full output.

## Build provenance

Precompiled ARM32 PIE binary targets `/system/bin/linker` and Android `libdl.so`. Both `.so` files are ARM32 ELF. Built with sandbox Clang / LLD. No NDK on your Mac. `build-sandbox.sh` documents reproducible build using a **link-time-only libdl.so stub**; this stub is not delivered and is not executed. Runtime links to M3's system `libdl.so`.

## What this doesn't establish

It does not establish safe recovery from real linker lock deadlocks, namespace acceptance within `com.android.bluetooth`, or safety of pausing a 48-thread Bluetooth service. Remote loading into that process remains prohibited.
