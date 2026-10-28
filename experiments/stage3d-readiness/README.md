# RetroBox Stage 3D D2b — passive loader readiness

D2a passed on M3 (`DLOPEN OK`, `DLCLOSE OK`). This follow-up inventories the **existing** Bluetooth process without attaching to it. It does not demonstrate remote `dlopen` or plugin injection.

## Execute from macOS

```sh
chmod +x inspect-m3.sh
./inspect-m3.sh 192.0.2.10:1080
```

Share the resulting `retrobox-d2b-readiness.txt` output. This gathers process credentials (`Uid`, `TracerPid`, `Seccomp`, etc.), SELinux domain, linker paths, already-loaded native libraries, and the existing Stage 3D files. No pairing keys, HCI payload, or process memory are dumped.

## Interpretation and hard boundaries

- `TracerPid=0` means no tracer is attached at inspection time. It **does not** establish that attaching would be permitted.
- SELinux `Permissive` does not bypass Linux credentials, dumpability, Android linker namespaces, or other kernel restrictions.
- Loading a library into a *new* process (D2a) is distinct from making the target Bluetooth process call `dlopen`.
- The library in `/data/local/tmp` may not be visible to the target linker namespace. A runtime-injection mechanism remains to be selected and proven.
- This script never uses `ptrace`, signals, linker injection, `am force-stop`, mount overlays, or filesystem writes on M3.

## Next gate

If readiness looks reasonable, create a **separate explicitly-invoked, reversible D2b probe** with: pre-test Bluetooth-health baseline, an inert add-on, minimal attachment time, an externally controlled watchdog/recovery command, and an unmistakable stop condition. Do not use this read-only report as proof injection is safe. Never globally bypass Bluetooth security.
