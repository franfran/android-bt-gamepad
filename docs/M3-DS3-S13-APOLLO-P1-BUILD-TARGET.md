# S13 Apollo P1 candidate build target, pinned source verified

At pinned public BPI H618 Android12 commit `250eabfc529518b7f26432663ed0a867ab2f625d`:
- `device/softwinner/apollo/AndroidProducts.mk` declares `$(LOCAL_DIR)/apollo_p1.mk` and `apollo_p1-userdebug`.
- `device/softwinner/apollo/apollo_p1.mk` declares `PRODUCT_NAME := apollo_p1` and `PRODUCT_DEVICE := apollo-p1`.
- `device/softwinner/apollo/BoardConfig.mk` identifies `TARGET_BOARD_PLATFORM := apollo` and `TARGET_BOARD_KERN_VER := 5.4`.

**Candidate**: `apollo_p1-userdebug` is a verified Soong lunch-menu choice in the public BSP. It is **not** verified as binary-equivalent to the installed OEM Oranth iMETBOX M3 Bluetooth runtime. Matching the M3-reported Apollo P1 build family is a useful lead, not evidence of identical product image, system libraries, linker namespace or Bluetooth service.

**Read-only operator steps for a complete BSP checkout** (do not run on M3):

```sh
python3 experiments/m3-source-first/full_bsp_build_preflight.py /path/to/full/android/tree
cd /path/to/full/android/tree
source build/envsetup.sh
lunch apollo_p1-userdebug
# Review resolved product config and 32-bit shared-library variants before attempting:
m libbluetooth -j2
```

The `m` command is a *future* controlled workstation build, not executed here. Capture build output, inspect Android ELF32 ARM library (if generated) against the original OEM library, including `DT_NEEDED`, exported symbols, symbol versions, architecture, load paths, binder/HIDL/JNI dependencies and run-time linker namespaces. Stop on divergence.

CI test `experiments/m3-source-first/test_pinned_apollo_p1_target.py` checks immutable product declarations but does not run `lunch`, Soong or Android compilation. Native DS3 authentication (0x22), Java HID bonded policy, UHID request completion and callback identity are independently unresolved. PR #51 remains Draft, PR #50 stays unmerged; deployment remains NO_GO.
