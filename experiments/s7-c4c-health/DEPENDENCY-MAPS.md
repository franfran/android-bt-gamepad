# S7-C4C-3 — JNI dependency map corroboration

This bounded, host-side, read-only tool compares the eight `DT_NEEDED` basenames already observed by the M3 owner against mapped-file basenames in the **current Bluetooth process**:

```bash
python3 experiments/s7-c4c-health/read-only-dependency-maps.py YOUR_ADB_SERIAL
```

It reads only current PID, status, comm, and maps through the existing root-capable Wi-Fi ADB transport, and revalidates the process after the snapshot. It outputs only the fixed eight dependency names, boolean `mapped`, and sanitized partition categories. No raw paths, addresses, private process data, or PID is emitted.

`mapped=true` means the named library appears in maps, **not** proof that the JNI loader resolved that specific library at startup or that a proposed add-on can reach it through the same namespace. An absent mapping is likewise not definitive evidence of a linker failure; vendor builds can differ. The instrument does not inspect linker internals, perform `dlopen`, restart Bluetooth, attach, or modify device state.

**After this check:** stop adding redundant read-only inventories. Hold a review to determine whether the remaining caller-namespace / add-on authorization / independent recovery gates can be satisfied without touching live Bluetooth, or whether to keep C4C-3 parked as NO-GO.
