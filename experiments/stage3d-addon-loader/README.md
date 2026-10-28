# RetroBox DS3 Stage 3D — Isolated ARM32 add-on loading PoC

## Goal

Verify that an ARM32 Android executable can use platform `libdl.so` to load, call and unload a tiny, inert ARM32 plugin on M3 Android 12 **inside its own new process**.

**This is D1 / an isolated version of D2, NOT proof that code can be loaded into `com.android.bluetooth`.** No hook, injection, ptrace, SELinux policy change, Bluetooth APIs, LinkKey, or authentication change is performed.

## Test on M3 (Mac terminal)

```sh
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

Expected if platform linker, library and loader all work:

```
RetroBox Stage 3D isolated loader (NOT Bluetooth injection)
DLOPEN OK
ABI: 0x00030001
Probe: 0x40760e4b
DLCLOSE OK
```

If the loader prints an error (including Android linker error), copy the complete output; do not attempt to load anything in the Bluetooth process. No modifications to Bluetooth are made.

To remove:

```sh
./cleanup-m3.sh 192.0.2.10:1080
```

## Implementation notes

- `retrobox_loader`: ARM32 PIE ELF with `/system/bin/linker` interpreter; has a `DT_NEEDED` for Android's `libdl.so`. `_start` uses ARM Linux `write` / `exit` system calls, avoids external libc dependencies.
- `libretrobox_ds3_addon.so`: ARM32 shared object with `retrobox_addon_abi()` and `retrobox_addon_probe()` exported and no external dependencies. It is deliberately inert.
- `libdl_link_stub.c`: LINK-TIME ONLY implementation used to generate an ELF linking shim in sandbox without NDK; **do not install its output `libdl.so` onto the device**. That output is not distributed. The loader's `DT_NEEDED` resolves to the platform `libdl.so` at runtime.
- These binaries have been statically inspected, **not executed on M3**. Compilation without the NDK is experimental; if the loader crashes or fails, do not infer anything about Bluetooth injection.

## Why this does not prove injection

`dlopen` in a fresh process merely checks whether platform linker/libdl can load a shared object. Injecting/hooking an existing system Bluetooth process additionally requires a validated loader/injection mechanism, dealing with linker namespaces, symbol resolution, Thumb instruction patching and rollback. None of those capabilities has been tested here.

## Security

No persistent services; no privileged process target; no automatic startup; only writes files under `/data/local/tmp/retrobox_stage3d`. No system Bluetooth files are touched.
