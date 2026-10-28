# RetroBox S7-C3 v3 — read-only ARM32 libdl address resolver

Corrects a false NO-GO in v2: Android Bionic `libdl.so` on the M3 has a fourth non-executable `PT_LOAD` at `vaddr=0x4000` that is not necessarily represented as a file-backed `/apex/.../libdl.so` mapping. A symbol resolver should require the exported function's *own* executable segment to be mapped with `x` permission; it should not reject an unrelated data/BSS segment.

This is still **read-only**: no remote execution, no `ptrace`, no injection; `injection_authorized` is always false. Resolving a candidate pointer is not proof of callable or permitted remote execution, linker namespace compatibility, or recovery.

On Mac (Python 3 + existing ADB only):

```sh
python3 -m unittest discover -v
python3 s7c3.py 192.0.2.10:1080 --json-out s7c3-v3-evidence.json
```

Expected symbol pointers (from previous M3 mapping only) are `load_bias + 0x1851` for `dlopen` and `load_bias + 0x1897` for `android_dlopen_ext`, *not* fixed addresses. Even a successful inspection leaves injection disabled.
