# RetroBox S7-C4B — Bluetooth target integration (fail-closed)

This is a **code deliverable**, but **not yet a Bluetooth injector**. It combines the previously verified ARM32 `libdl` symbol resolver with live target identity checks and the S7-C4A staged add-on SHA-256 comparison. It issues one JSON evidence bundle, detects PID/mapping race conditions and refuses to authorize injection.

## Usage from Mac (no Android NDK)

S7-C4A staged addon must still be present from your previous PASS.

```bash
python3 -m unittest discover -v
python3 s7c4b.py 192.0.2.10:1080 --output s7c4b-evidence.json
```

This does NOT call `ptrace`, `dlopen` or any write operation on the M3. It runs only read-only `adb` commands.

## Engineering boundary

S7-C1's return trap is located in its own fork-owned test process, and **cannot** be assumed accessible in Android's existing Bluetooth service. The working `dlopen` address is also per-process/ASLR and requires revalidation; restoring registers after a call hangs is not safe rollback for linker internal state.

The target-specific remote loader requires a safe target-side execution/return mechanism, target-owned scratch lifecycle, explicit on-device recovery, and an accepted namespace path. **These are not implemented in this deliverable.** No arbitrary-PID injection binary is included, and old `inject` builds must not be used.

Avoid treating the clean inspection report as proof that injection is safe. Any future attempt should be one-time and explicitly operator-initiated, with a locally available recovery path. A restart may reset ephemeral mappings but not repair corrupted on-disk state if any permanent changes occur.
