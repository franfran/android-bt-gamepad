# S10 pinned Android 12 Soong build-graph audit

Verified against public BSP commit `250eabfc529518b7f26432663ed0a867ab2f625d`, `system/bt/main/Android.bp`.

The `libbluetooth` target is `cc_library_shared` with `fluoride_defaults`, headers, platform HIDL/AIDL and generated dependencies. It links `libbtif`, `libbt-bta`, `libbt-stack` through `whole_static_libs`, and includes `libbluetooth_gd` and `libbluetooth_rust_interop`. This means building `libbluetooth.so` is **not equivalent** to compiling only the modified BTIF translation units: a complete matching Android12 source checkout, Soong/Ninja generation, Rust toolchain, generated headers, platform modules, correct product/board target and 32-bit variant must all resolve.

The new `test_pinned_soong_module.py` audits the actual pinned `main/Android.bp` source and fails closed if its target/dependency anchors change. This is a **source graph check, not a build**.

Suggested future proof for full-build gate, only in a properly provisioned local Android BSP checkout (do NOT run against M3):

```sh
source build/envsetup.sh
lunch <verified_h618_arm32_product_target>
m libbluetooth -j2
```

The lunch target must be determined from a complete BSP checkout; do not guess from device model or substitute host `armv7a-none-eabi` output. Capture module build log, actual installed path/ELF header, SONAME, NEEDED libraries, symbols, linker namespaces and compare against original M3 `libbluetooth.so`. ARM32 compilation success alone does **not** authorize replacement. Native HID authentication / bond / UHID callbacks are independent NO_GO gates.

No build was run on a complete Android tree, no M3 operations and no merge. PR #51 remains Draft, PR #50 separate.
