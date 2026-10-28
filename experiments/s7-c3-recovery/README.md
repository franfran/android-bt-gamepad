# RetroBox Stage 3D — S7-C3b/C3c

This package is a **read-only Bluetooth execution-safety snapshot** and an **executable failure-state model**. It does **not** implement Bluetooth injection; do not interpret its passing tests as evidence that injecting into Bluetooth is safe.

## Run on Mac (Python 3, ADB; no NDK)

```bash
python3 -m unittest discover -v
python3 s7c3bc.py 192.0.2.10:1080 --output s7c3bc-evidence.json
python3 s7c3bc.py --scenario timeout-during-linker --output s7c3bc-timeout.json
```

The device inspection uses `adb shell su 0` read commands, enumerates threads, checks UID / PID / mappings, and fails closed. **Do not use the old Bluetooth `inject` binary.** The state-machine scenarios are host-only simulations, not Android linker-lock tests.

## Safety contract

- The previous S7-C1 isolated loader proved private scratch allocation and `dlopen` in a *fork-owned child*, not the Bluetooth service.
- If an injected `dlopen` hangs or stops unexpectedly, register restoration cannot undo linker-internal changes. The code marks this `QUARANTINE` and `restart_required`, never `safe_to_retry`.
- `restart_required` is a *risk classification*, not an instruction to automatically kill/restart Bluetooth. Any actual recovery needs human-approved procedures, verification and physical access.
- Linker namespace acceptance and contention recovery remain unproven; authorization always stays **false**.
- No network access besides read-only ADB. No persistent file is deployed to the TV box.

## Next implementation gate

Add controlled linker-contention tests on an owned process with documented lock ownership; verify namespace behavior without touching Bluetooth; implement an external-service recovery runbook before any one-shot injection is considered.
