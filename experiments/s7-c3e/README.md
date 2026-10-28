# RetroBox S7-C3e v2 — concurrent dlopen observations

This is a **prebuilt ARM32** test for the iMETBOX M3, with source. No Android NDK needed on the Mac. It runs only a fork-owned multi-threaded test child. It does **not** attach to Bluetooth, inject libraries into other processes, or modify system libraries.

## Why v2

The M3 v1 output showed B's `dlopen(fast.so)` completing *before* A's slow constructor finished in both scenarios. The v1 harness incorrectly treated that as a failure by assuming constructor execution was globally serialized. That assumption is not warranted. v1 also immediately checked background tick progress after early B completion, causing a timing-sensitive false negative.

v2 treats the observed order as a **fact**, not an automatic pass/fail for a presumed mutex. It waits until both calls return in the normal scenario; in the stall scenario, it checks that A is still running at its 300ms deadline and reports QUARANTINE/SAFE_TO_RETRY=false regardless of whether B finished. It waits 120ms before checking background ticks.

This test **does not establish** which Bionic linker locks were held. A constructor delay is not proof of a held linker mutex, and an owned child's watchdog+kill is not a safe recovery procedure for the live Bluetooth process.

## Run on Mac

```sh
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

Both executable and .so files are uploaded afresh on every run. Previous `/tmp` or `/data/local/tmp` contents are not required. The normal scenario waits up to 1800ms, the stall scenario checks a 300ms deadline. Read the observation lines to interpret the result; don't infer Bluetooth injection readiness.

## Status

- Compiled with sandbox Clang 17/LLD to Android ARM32 ELF and checked with `file`.
- Shell syntax checked.
- **Not tested on the M3 yet.**
- Bluetooth inert add-on injection remains **NO-GO** pending separate namespace and live-process recovery validation.
