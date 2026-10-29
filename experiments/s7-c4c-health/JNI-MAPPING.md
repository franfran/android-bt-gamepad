# C4C-3 read-only JNI mapping snapshot

Run on the Mac against the existing Wi-Fi ADB connection:

```bash
python3 experiments/s7-c4c-health/read-only-jni-mapping.py YOUR_ADB_SERIAL
```

The tool checks current Bluetooth PID/UID/comm/TracerPid, reads its `/proc/PID/maps` once, checks process identity afterwards, then reports only whether the **exact basename** `libbluetooth_jni.so` appears, and sanitized partition categories for matching mappings. No PID, memory address, raw maps, other paths or network identifiers are output. Errors fail closed and are generic.

Mapping evidence is **not** a call trace: `jni_library_mapped=true` does not establish how the JNI library was loaded, which ClassLoader or dynamic linker namespace was involved, or whether a future add-on can load from `/data/local/tmp`. `false` does not establish Bluetooth lacks a native/JNI stack: OEM versions can link differently. Namespace acceptance and recovery remain **UNVERIFIED**; live Bluetooth operations remain **NO-GO**.

The tool performs no write, ptrace, linker call, service restart or injection. Wi-Fi ADB first; USB last-resort only.
