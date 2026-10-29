# C4C-3 — ELF JNI DT_NEEDED inspection

After M3 read-only mapping confirmed `libbluetooth_jni.so` in SYSTEM, inspect the immutable file's declared ELF dependencies from Mac over Wi-Fi ADB:

```bash
python3 experiments/s7-c4c-health/read-only-jni-needed.py YOUR_ADB_SERIAL
```

This host-side Python 3.8+ tool reads **only** the fixed `/system/lib/libbluetooth_jni.so` file with a bounded ADB command and parses ELF32 little-endian `PT_DYNAMIC`, `DT_STRTAB` and `DT_NEEDED` without running or loading the binary. Output includes only validated library basenames. It does not transmit raw ELF to GitHub or print device identifiers, addresses or arbitrary strings. Invalid or OEM-specific formats fail closed.

**Limitations:** A library's declared dependencies are not proof of which namespace actually resolved them, or that an extra add-on from `/data/local/tmp` can load. ELF file path corresponds to previously observed SYSTEM JNI mapping only by path/category inference; this tool does not authenticate the mapped inode/build ID. A valid DT_NEEDED list does not prove dependencies successfully resolved via the same caller namespace that a hypothetical later direct dlopen would use.

No service restart, attach, ptrace, code execution inside Bluetooth, file writes, or injection. Live Bluetooth decision remains NO-GO. Wi-Fi ADB first, USB last resort.
