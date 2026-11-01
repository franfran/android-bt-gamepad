# S14 — Genuine Android 12 ARM32 Soong build path (offline, not yet executed)

## Source audit and correction

Pinned monorepo `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d` exposes Android platform root directories (`build/`, `system/bt/`, `prebuilts/clang/`, `device/`), **not** a `.repo` directory. S12's prior requirement for `.repo` rejected a correctly cloned upstream BPI monorepo. Commit `500288e7` fixes this while still pinning the actual Git commit. The script is only a structural/identity gate.

The pinned upstream [README](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/README.md) explicitly warns that GitHub's 100 MB per-file limit forces users to separately download missing oversized files and place them at correct paths. Merely passing preflight, or cloning this repository, is **not** evidence of a complete compilable BSP. The README recommends a Sinovoip Docker image named `bpi-build-android-11`, despite the repo being Android12; its exact suitability is not verified. Its documented board build examples are Banana Pi targets, not an M3 factory image. We do not run `pack` or flash.

## Actual verified lunch candidate and architecture caution

`device/softwinner/apollo/AndroidProducts.mk` declares `apollo_p1-userdebug`; `apollo_p1.mk` names `apollo_p1`. The common `BoardConfig.mk` sets ARM64 kernel architecture and `TARGET_SUPPORTS_32_BIT_APPS := true`, which **does not guarantee** this module gets a 32-bit variant. An ARM64 kernel is consistent with an ARM32 user-space Bluetooth library. The Soong-selected `TARGET_ARCH` and `TARGET_2ND_ARCH` must be read after lunch, and the produced **system/lib** file checked as ELF32 ARM. The build script does this.

## Reproducible host-only path

On a well-provisioned Linux Android build workstation (not the M3):

```sh
git clone https://github.com/BPI-SINOVOIP/BPI-H618-Android12.git /data/BPI-H618-Android12
cd /data/BPI-H618-Android12
git checkout --detach 250eabfc529518b7f26432663ed0a867ab2f625d
git rev-parse HEAD
# Follow the pinned upstream README instructions to restore oversized files.
# Do not commit downloaded proprietary or oversized BSP blobs to RetroBox.
# In a separate clone of android-bt-gamepad with PR #51 checked out:
bash experiments/m3-source-first/build_bsp_arm32_offline.sh \
  /data/BPI-H618-Android12 /data/m3-bsp-evidence
```

The script verifies pinned source, selects the **source-declared** candidate `apollo_p1-userdebug`, uses `BOARD_BUILD_BOX=true` (box-oriented selection), inspects resolved arch, invokes `m libbluetooth -j2`, and fails closed unless `system/lib/libbluetooth.so` exists and is ELF32 ARM. Captures build log, architecture selection, baseline ELF and readelf evidence outside source tree. Build errors from absent oversized upstream files/dependencies must be reported as genuine blockers rather than patched over with arbitrary vendor substitutes.

**Baseline caveat:** this builds the unmodified pinned BSP. S9 is currently a proven offline three-file transformation, not a patch automatically applied to a BSP workspace. Establish a baseline Soong build first, then deliberately apply/review S9 source changes in a separate offline workspace and rebuild; do not imply the first ELF contains a DS3 fix.

## What remains unverified

No complete BSP checkout on an actual Android build host, no successfully run Soong build, no produced ARM32 ELF, no binary comparison to the private original M3 library. The public repo may need additional missing files or build-system fixes. Disk capacity and RAM must be checked on the chosen host before starting; full Android trees can be large, and precise resource needs for this particular BSP are not yet measured.

Gate A native per-device authentication, gate B Java `BOND_BONDED` and virtual-unplug behavior, and gate C UHID request-specific callback ownership remain independent and unsolved. Device deployment, library replacement, injection, global Bluetooth security changes and merging remain **NO_GO**; PR #50 stays unmerged.
