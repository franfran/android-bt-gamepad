# S12 complete Android BSP build preflight

Added `experiments/m3-source-first/full_bsp_build_preflight.py` to run **read-only** in a locally provisioned Android BSP source checkout, without Bluetooth/device access.

Usage:
```sh
python3 experiments/m3-source-first/full_bsp_build_preflight.py /absolute/path/to/full/android/source
```

Checks: repo-managed Android checkout, `build/envsetup.sh`, `build/soong/soong_ui.bash`, pinned BTIF implementation/Soong files, Clang prebuilts, and `system/bt` Git HEAD exactly `250eabfc529518b7f26432663ed0a867ab2f625d`. Missing/unknown items fail closed. A CI negative fixture proves incomplete trees are refused.

**Important limits:** passing preflight is not proof that a valid H618 lunch product exists, Android 32-bit variant is enabled, all dependencies resolve, the tree is internally consistent, or a `libbluetooth.so` build will succeed. No actual full Android tree was available in the execution environment; no Soong build was performed. Full BSP checkout/storage and a verified product target are required separately.

After a full build by an authorized operator, compare resulting ARM32 ELF against original OEM `libbluetooth.so` read-only (ELF class, machine, SONAME, DT_NEEDED, exported symbols, linker namespaces and dependencies); no replacement is authorized. UHID callback identity, native DS3 auth and Java bond policy remain independent NO_GO gates. PR #51 Draft, PR #50 unmerged, M3 untouched.
