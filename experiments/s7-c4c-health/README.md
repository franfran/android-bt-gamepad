# C4C-3 read-only Bluetooth health check

**Operator approved scope: observation + recovery procedure design only.**
This is not Bluetooth injection, a restart, a pairing fix or proof of recovery.

From the repository checkout on Mac (Python >=3.8, existing ADB, no NDK):

```bash
adb devices -l
python3 experiments/s7-c4c-health/read-only-health.py YOUR_ADB_SERIAL
```

**Do not type an IP from a sample; use the actual ADB serial shown locally.**
The utility reads only `pidof com.android.bluetooth`,
`/proc/PID/comm`, `/proc/PID/status`, and `/proc/PID/maps` via
`adb exec-out su 0 sh -c`. PID is validated decimal and refreshed.
It checks comm, UID 1002, thread count and `TracerPid=0`. It returns
sanitized JSON: booleans and thread count, but **no PID, MAC, home IP,
memory address, raw maps or secret**. No `ptrace`, `kill`,
`setprop`, `service call`, injection or filesystem write.

Any read failure, suspicious identity, mapping absence, ambiguous or
changed PID produces exit code 2 and a sanitized NO-GO error. It does
**not** assert the linker namespace will permit an add-on and cannot
establish whether Bluetooth survives a future crash.

Tests (host only): `python3 -m unittest discover -s experiments/s7-c4c-health/tests -v`.

## Independent recovery checklist (not executed)

1. Verify **existing** Wi-Fi ADB access and keep physical power/UI
   access. Wi-Fi ADB is independent of the Bluetooth service but may fail
   if the device, Wi-Fi or ADB daemon becomes unresponsive.
2. Separately establish that **USB ADB actually works** on this M3.
   Simply plugging in a USB cable does not guarantee a USB-debugging
   interface; do not claim verified wired recovery without a real test.
3. Record a clean baseline from this read-only check and private notes
   about transport availability.
4. If a *later separately approved* Bluetooth experiment disrupts the
   service, do not auto-retry injection. Use the independently verified
   access path to diagnose the process and follow a device-specific,
   owner-reviewed service-recovery plan.
5. Any destructive recovery step or Bluetooth service restart requires
   **another explicit approval** and pre-defined post-checks. The
   read-only utility never carries out a recovery action.

See `docs/S7-C4C-3-HAZARD-ASSESSMENT.md` for the governing NO-GO gate.
