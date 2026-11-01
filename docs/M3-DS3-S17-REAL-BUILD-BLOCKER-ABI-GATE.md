# S17 — BSP resource reality and offline OEM ELF comparison

BPI upstream GitHub repository metadata reports `size=21156134` KiB (approximately 21.2 GB decimal) at inspection time. This is a GitHub reported repository-size metric, **not** a measured local source checkout size. Pinned README additionally warns some files exceed GitHub's 100 MB limit and must be restored separately. So a Linux builder needs substantially more disk than repository-size alone, especially for Android Soong intermediates. The investigation container had ~30 GB free, ~5.8 GiB RAM and no swap; it is **not a viable complete Android BSP build host**. No Android compilation attempted or claimed.

The new `compare_m3_bluetooth_elf.py` is intended to run **after** an authentic Android ARM32 Soong build with the owner's original private OEM library available locally:

```sh
python3 experiments/m3-source-first/compare_m3_bluetooth_elf.py \
  /private/m3-original-2024-libbluetooth.so \
  /data/retrobox-bsp-evidence/libbluetooth-arm32-baseline.so \
  --json-output /data/retrobox-bsp-evidence/oem-vs-baseline-abi.json
```

It verifies archived OEM SHA256, ELF32 ARM identity, compares SONAME and DT_NEEDED, and identifies lost OEM exported dynamic symbols and candidate new undefined dynamic imports. Differences are reported as NO_GO for static ABI compatibility pending inspection. A clean static screen is **not** a runtime pass: additional symbol versions, linker namespaces, JNI, vendor HAL integration and service/framework behavior remain unverified. Do **not** upload the proprietary OEM binary to the public repository.

Next required work is provisioning an adequately sized Linux Android12 workstation, obtaining the pinned upstream BSP and its separately distributed oversized files, running baseline Soong build and then S9 Soong rebuild. The source-first integration and offline ELF analysis are ready for that stage; no executable `libbluetooth.so` has yet been produced. Gate A native DS3 security, gate B Java bond policy and gate C UHID completion identity remain distinct unresolved blockers. PR #50 and PR #51 stay unmerged; no M3 operations.
