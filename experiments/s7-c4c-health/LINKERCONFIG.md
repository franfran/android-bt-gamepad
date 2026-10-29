# Static linkerconfig inspection (C4C-3)

This tool is read-only and **cannot** establish linker namespace acceptance inside the live Bluetooth process. Android 11+ generates linker config under `/linkerconfig` at boot; OEM configurations vary. It reads only two fixed candidate text files and reports sanitized booleans/counts, never raw paths or policy values.

```bash
python3 experiments/s7-c4c-health/read-only-linkerconfig.py YOUR_ADB_SERIAL
```

No library execution, linkerconfig regeneration, service restart or injection is performed. `candidate_files_read=0` is valid evidence of absence/inaccessibility of these *specific* candidates, **not** proof that the device has no linker configuration. Even if namespace keys are present, Bluetooth namespace selection, add-on path permission and actual `dlopen` acceptance remain `UNVERIFIED`. Owner's Wi-Fi ADB remains the preferred transport; USB is a last resort. See `docs/S7-C4C-3-NAMESPACE-EVIDENCE.md` and Issue #6. Avoid publishing raw configuration, process maps, IDs or addresses.

Reference: Android AOSP `system/linkerconfig` README and Android linker namespace documentation (Android 11+).
