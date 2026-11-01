# S15 — Baseline → patched Android Soong ELF, offline only

**Status: build scripts committed, full BSP build NOT RUN.**

This stage closes an engineering gap: S9's three-file integration used to exist as a network-fetched host fixture rather than an apply operation for a genuine pinned Android tree. The new `apply_s9_to_pinned_bsp.py` imports the existing deterministic S9 `transform()` from `test_integrated_btif_allocation_source.py`, reads all three source files directly from the *local* checkout, verifies pinned HEAD and known blob hashes, rejects dirty/symlink source files and mismatched anchors, and writes only the three planned BTIF files. It makes **no network or device calls**. This is **not** completion identity propagation, nor a deployable DS3 fix.

## Controlled build-host sequence

On a Linux Android build host with the complete pinned upstream tree and all required oversized files restored:

```sh
# RetroBox PR #51 checkout:
RB=/path/to/android-bt-gamepad
BSP=/data/BPI-H618-Android12
EVIDENCE=/data/retrobox-bsp-evidence

# Build unmodified BSP first and capture ELF32 evidence.
bash "$RB/experiments/m3-source-first/build_bsp_arm32_offline.sh" "$BSP" "$EVIDENCE" baseline

# Only after baseline has really passed: modify three BTIF sources in the local BSP.
python3 "$RB/experiments/m3-source-first/apply_s9_to_pinned_bsp.py" "$BSP"
git -C "$BSP" diff -- system/bt/btif/co/bta_hh_co.cc \
  system/bt/btif/src/btif_hh.cc system/bt/btif/include/btif_hh.h > "$EVIDENCE/s9-source.diff"

# Rebuild using Android Soong; preserve patched ELF separately.
bash "$RB/experiments/m3-source-first/build_bsp_arm32_offline.sh" "$BSP" "$EVIDENCE" s9
cmp "$EVIDENCE/libbluetooth-arm32-baseline.so" "$EVIDENCE/libbluetooth-arm32-s9.so" \
  && echo "WARNING: identical ELF outputs; investigate source/build selection" \
  || echo "ELF files differ; inspect sections, symbol tables and dependency tables"
```

The baseline and S9 runs share the same BSP working tree and output directory, so Soong may use incremental rebuilds. An identical ELF does not prove correct source ownership and an ELF difference does not prove a functional DS3 fix. Keep logs and diff to verify which source revision was built. For stronger provenance, repeat patched build in a clean separately cloned workspace with a separate `OUT_DIR`.

`build_bsp_arm32_offline.sh` now requires an explicit (or default `baseline`) label to prevent accidental overwrite of the baseline ELF. It still checks the final ELF class and architecture, and aborts if it cannot find `system/lib/libbluetooth.so`. If the system image output path differs, investigate Soong module installation rather than claiming build success.

## Remaining hard blockers

- Full BSP source clone and missing >100 MB files have **not** been provisioned here.
- `apollo_p1-userdebug` is a verified public product candidate, but Soong's ARM32 `libbluetooth` variant and module installation path remain unverified until first build.
- No compiled Android ARM32 `libbluetooth.so` has been obtained yet; no OEM ABI comparison can be claimed.
- S9 only propagates **local allocation/queue acceptance**. Native DS3 authentication (0x22), Java HID Host bonded policy, UHID reply request identity, and remote handshake attribution remain unresolved.
- PR #51 remains Draft and PR #50 remains unmerged; no M3 modifications or deployment are authorized.
