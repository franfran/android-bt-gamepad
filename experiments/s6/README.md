# RetroBox Stage 3D S6 — Bluetooth injection safety gate

## Scope

S1–S5 have passed isolated M3 tests. S5 verifies remote `dlopen()` in a fork-owned child with 4 workers. It does **not** validate remote `dlopen()` into `com.android.bluetooth` (previously 48 threads). This deliverable is a **read-only, fail-closed safety audit**, not a Bluetooth injector.

## Run on Mac (no NDK, no Python packages)

```sh
python3 check.py 192.0.2.10:1080 | tee s6-audit.txt
```

Prerequisites: ADB reachable and M3 root accessible using `su 0`. No deployment to M3. The script uses only `adb shell` commands (`pidof`, `cat`, `ls`) and has no code path that attaches, injects, patches, changes Bluetooth, or writes files on the device. It re-reads the PID to detect restarts.

## How to interpret

- `PASS: read-only audit completed` means device observation was internally consistent, **not that injection is safe**.
- `INJECTION GATE: NO-GO` is intentionally unconditional for this tool. It is not a hardware incompatibility claim.
- Do not use the old `retrobox-stage3d-d2b2d-b-arm32.zip` `inject` mode. Its remote stack scratch and unbounded target wait remain unsafe for a production Bluetooth process.
- S5 borrowed the local `dlopen` address across `fork`; a Bluetooth process has separate ASLR mapping and linker namespace.

## Engineering conditions for any future Bluetooth inject gate

1. Verify remote `dlopen` candidate against original ELF symbol + executable mapping, per current PID. The previous validator computed `0xf3961851` only for its sampled PID/mapping, not as a persistent address.
2. Allocate and guard **target-owned** scratch memory, never use active Bluetooth stack slots. Verify cleanup on both success and failure.
3. Define a deterministic failure policy. A remote `dlopen` timeout may leave linker-owned mutexes or global state inconsistent; register restoration alone cannot make this safe. Automatic retries must remain disabled.
4. Do not assume freezing all 48 threads is a solution: that can deadlock if any paused thread holds the linker lock. Verify actual service-specific thread/lock behavior on a non-production replica or prefer process startup extension rather than runtime injection.
5. Verify linker namespace acceptance for the plugin path and ensure the plugin does not weaken authentication for other devices.
6. Define human-supervised rollback. Deleting a file does not unload an already mapped `.so`; a controlled restart may be necessary and could interrupt Bluetooth-connected devices.

**Decision:** The S1–S5 technical prerequisites are valuable, but they are insufficient to authorize injecting a live 48-thread Bluetooth service. Keep `/system/lib/libbluetooth.so` unchanged.
