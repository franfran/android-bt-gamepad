# RetroBox Stage 3D S7-A/S7-B — integration and safety contract

This package is a **development artifact, not a Bluetooth injector**. It contains a read-only device-aware integration assessor, a static source audit for the unsafe D2b-2d-B prototype, and a test suite. It does NOT write to the M3, call ptrace, or start any process injection.

## Run on your Mac (no Android NDK)

```sh
python3 s7_gate.py 192.0.2.10:1080 --json-out s7-evidence.json
python3 s7_gate.py --fixture s6-audit.txt --source legacy-bt-injector.c --json-out legacy-review.json
python3 -m unittest discover -v
```

The second command is optional: copy the earlier S6 report and old injector C source into the directory first, or supply their actual paths. The CLI always refuses to authorize Bluetooth injection.

## Engineering contract for S7-A integration

The target loader shall not use the target's existing stack memory for pathname or parameters. It must remotely allocate target-owned memory via `mmap2`, guard boundaries via `mprotect`, verify each `PTRACE_PEEKDATA` using the ARM raw syscall output-buffer convention, and release via `munmap` only when safe. All ARM32 registers (including CPSR Thumb bit) must be saved before intervention and restored at a verified stop. It must independently parse the target ELF PT_LOAD segments, compute ASLR-correct address and verify the candidate is inside an executable mapping. Every PID/TID and library identity must be rechecked immediately before changes.

S4 validated these primitives **only in an owned isolated child**, not against Bluetooth. Reusing them as-is without isolated integration testing is not sufficient.

## Engineering contract for S7-B linker and thread safety

Do not `dlopen()` if any unverified thread can hold a linker lock needed by the injected call; all-threads sleeping is NOT proof of lock availability. Detaching all threads and hoping is not a safe recovery strategy. A timeout during linker execution does NOT imply linker internals are in a safely reversible state; register restoration alone cannot undo mutexes, TLS, constructor changes, partially loaded ELF state, or namespace modifications.

An Android linker namespace may reject the plugin even if S5 loaded it in a regular test process. A namespace test must preserve the actual Bluetooth process caller context, and any trial affecting Bluetooth requires explicit blast-radius and recovery validation. Never turn a policy failure into a request for production injection.

## S7-C strict release gate (not implemented)

Before a Bluetooth-specific inert load test is considered: (1) code-reviewed memory and thread lifetime handling; (2) strong fail-stop conditions; (3) no auto-retry or autostart; (4) documented local recovery without opening a network port; (5) physical ability to restart the box; (6) snapshots of original `.so` hashes and service health; (7) separate consent for one-shot Bluetooth interruption; (8) rollback verification, including service restarts. A safe detachment requires more than returning to the same PID.

## Known unsafe legacy prototype

`retrobox-stage3d-d2b2d-b-v3/bt_inert_inject.c` used `SP+256` scratch, a blocking `wait4`, a NULL remote return address and raw PEEKDATA return semantics. **Never run the old `inject` mode**.

## Interpretation

S1-S5 and S6 are already successfully tested. This S7-A/B package gives the actual code-level risk checks and reproducible assessment to guide the next implementation, but it does not claim to solve linker-lock recovery or prove Bluetooth injection safe.
