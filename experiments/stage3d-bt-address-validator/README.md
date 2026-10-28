# RetroBox Stage 3D — D2b-2d-B ARM32 linker address validator

Read-only follow-up to the M3 `libdl.so` discovery failure. **Not an injector.** This does not ptrace, modify memory, run remote calls, or touch Bluetooth pairing.

## Run on macOS

Requirements: Python 3.8+ and `adb` in PATH. No Python packages or Android NDK are required.

```bash
python3 validate.py 192.0.2.10:1080 | tee d2b2d-b-address-validation.txt
```

The script dynamically fetches the Bluetooth PID, checks `droid.bluetooth`, UID=1002 and `TracerPid: 0`, reads `/proc/PID/maps`, pulls the **original** APEX `libdl.so` to the current directory if absent, and parses its ELF32 PT_LOAD and .dynsym structures with the Python standard library.

It finds the executable file offset for the `dlopen` symbol and translates it through the actual executable `/proc/PID/maps` entry, **not** by assuming all PT_LOAD segments share an unmodified virtual-address offset. This produces a candidate only: a file-offset translation is not proof that a live remote function call will be safe or that Android's linker namespace will permit the add-on.

The script does not call `su -c`; it uses this box's `su 0`. It never relies on previously uploaded binaries in `/data/local/tmp`; its only optional local cache is `libdl-m3-readonly.so` in the directory where you run it. Delete that file to refresh the ELF from the device after an OS change.

Do not run the `inject` mode from the original D2b-2d-B package. That path still needs independent memory, thread and timeout hardening.
