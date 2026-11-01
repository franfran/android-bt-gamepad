# S18 — Ubuntu 22.04 x86_64 Android12 BSP build-host playbook

This document covers **offline library builds only**, not firmware, device operations, `pack`, or flashing.

Recommended host: Ubuntu 22.04 LTS x86_64, 8 vCPU, 32 GiB RAM, 300 GiB+ SSD (500 GiB preferable). These are provisioning recommendations, not measured minimums for the BPI tree. Alternative Ubuntu revisions may need troubleshooting. Use an ext4 disk; verify `df -h` and `free -h`.

## Packages

From the PR #51 checkout:

```bash
bash experiments/m3-source-first/setup_ubuntu_2204_host.sh
```

Android12 includes prebuilts; system OpenJDK11 is a fallback, not an instruction to force a Java version. No Android Studio or Repo launcher is necessary for the monolithic pinned BPI Git checkout.

## Source acquisition

```bash
mkdir -p ~/retrobox
cd ~/retrobox
git clone https://github.com/franfran/android-bt-gamepad.git
cd android-bt-gamepad
git switch feat/m3-ds3-source-first
RB="$PWD"
sudo mkdir -p /data/android /data/retrobox-bsp-evidence
sudo chown -R "$(id -u):$(id -g)" /data/android /data/retrobox-bsp-evidence
cd /data/android
git clone https://github.com/BPI-SINOVOIP/BPI-H618-Android12.git
cd BPI-H618-Android12
git checkout --detach 250eabfc529518b7f26432663ed0a867ab2f625d
git rev-parse HEAD
```

The upstream pinned [README](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/README.md) warns GitHub omits >100 MB files; source will probably require the upstream separate oversized-file archive restored to exact paths. Inspect archives before copying; record all missing file paths/hashes privately. `full_bsp_build_preflight.py` checks structure and pinned commit but **cannot detect all missing binary/toolchain prebuilts**.

## First real ARM32 Soong build

```bash
RB="$HOME/retrobox/android-bt-gamepad"
BSP="/data/android/BPI-H618-Android12"
EVIDENCE="/data/retrobox-bsp-evidence"
python3 "$RB/experiments/m3-source-first/full_bsp_build_preflight.py" "$BSP"
bash "$RB/experiments/m3-source-first/build_bsp_arm32_offline.sh" "$BSP" "$EVIDENCE" baseline
```

It uses the verified `apollo_p1-userdebug` candidate, `BOARD_BUILD_BOX=true`, selects module `libbluetooth` and checks for `system/lib/libbluetooth.so` ELF32 ARM output. **No proof this particular target has the required 32-bit installed variant until build runs**. If Soong fails or no ELF32 output appears, retain logs rather than altering systemwide OEM compatibility assumptions.

## S9 rebuild only after baseline success

```bash
python3 "$RB/experiments/m3-source-first/apply_s9_to_pinned_bsp.py" "$BSP"
bash "$RB/experiments/m3-source-first/build_bsp_arm32_offline.sh" "$BSP" "$EVIDENCE" s9
```

Offline OEM comparison only if owner-original private ELF is available to the build host:

```bash
python3 "$RB/experiments/m3-source-first/compare_m3_bluetooth_elf.py" \
  /private/m3-original-2024-libbluetooth.so \
  "$EVIDENCE/libbluetooth-arm32-baseline.so" \
  --json-output "$EVIDENCE/oem-vs-baseline-abi.json"
```

Do not put original OEM ELF or any private board identifiers in GitHub commits. Baseline/S9 builds are offline research and do not fix authentication, Java bond policy or UHID completion attribution. No device deployment or PR merge approved.
