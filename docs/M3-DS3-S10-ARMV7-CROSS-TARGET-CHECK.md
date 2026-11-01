# S10 ARMv7 cross-target source-fragment compilation

This checkpoint improves S9 verification without claiming a complete Android build. The `test_s9_armv7_cross_compile.py` script invokes the existing S9 source transformation and host compilation, retains the **actual generated source slices** of the BTIF helper, original wrapper and UHID ingress, then compiles that same extracted code to an `armv7a-none-eabi` object using Clang. It requires `readelf -h` to show `ELF32` and `Machine: ARM`.

This matters because GCC/Clang host compilation on x86_64 does not check that the modified C++ functions can be emitted for ARM32.

**Precise limits:** This test uses bare-metal armv7a-none-eabi rather than the Android `armv7a-linux-androideabi` target or matching OEM NDK/Soong toolchain, mocks all Android/BTA dependencies, does not link a shared library, does not use OEM source headers, and does not evaluate ELF dependencies, C++ ABI, Bluetooth callback identity or actual DS3 connectivity. A green result proves only a synthetic ARM32 object from source slices. In particular, it is not `libbluetooth.so` and cannot be flashed or installed.

The next meaningful build target is full pinned BSP Soong `libbluetooth` with exact Android12 configuration and ABI comparison against the user's privately held OEM ELF, followed separately by unresolved per-DS3 native authentication and Java bond policy. No M3 operation, binary replacement, security relaxation or merge is authorized.
