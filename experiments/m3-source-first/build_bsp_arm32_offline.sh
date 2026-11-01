#!/usr/bin/env bash
# Offline build host only. Never installs, flashes, or interacts with M3.
set -euo pipefail
if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: bash $0 /absolute/path/to/BPI-H618-Android12 /absolute/path/to/evidence-dir [baseline|s9]" >&2
  exit 2
fi
LABEL="${3:-baseline}"
[[ "$LABEL" == "baseline" || "$LABEL" == "s9" ]] || { echo "Unknown label" >&2; exit 2; }
ROOT="$(cd "$1" && pwd -P)"
mkdir -p "$2"
EVIDENCE="$(cd "$2" && pwd -P)"
[[ ! -e "$EVIDENCE/libbluetooth-arm32-$LABEL.so" ]] || { echo "NO_GO: evidence already exists (no overwrite)" >&2; exit 2; }
[[ "$EVIDENCE" != "$ROOT" && "$EVIDENCE" != "$ROOT/"* ]] || { echo "Evidence must be outside BSP source tree" >&2; exit 2; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
python3 "$SCRIPT_DIR/full_bsp_build_preflight.py" "$ROOT" | tee "$EVIDENCE/preflight-$LABEL.log"
cd "$ROOT"
# Do not mistakenly label an already patched output as pristine baseline.
BTIF_FILES=(system/bt/btif/co/bta_hh_co.cc system/bt/btif/src/btif_hh.cc system/bt/btif/include/btif_hh.h)
if [[ "$LABEL" == "baseline" ]] && [[ -n "$(git status --porcelain -- "${BTIF_FILES[@]}")" ]]; then
  echo "NO_GO: BTIF source is modified; refusing baseline label" >&2
  exit 1
fi
if [[ "$LABEL" == "s9" ]] && [[ -z "$(git status --porcelain -- "${BTIF_FILES[@]}")" ]]; then
  echo "NO_GO: BTIF source unchanged; refusing s9 label" >&2
  exit 1
fi
git diff -- "${BTIF_FILES[@]}" > "$EVIDENCE/btif-source-$LABEL.diff"
git rev-parse HEAD > "$EVIDENCE/bsp-head-$LABEL.txt"
# This candidate is directly declared by the pinned BSP AndroidProducts.mk.
export BOARD_BUILD_BOX=true
# Android build shell utilities are defined by envsetup.sh.
source build/envsetup.sh
lunch apollo_p1-userdebug
printf 'TARGET_PRODUCT=%s\nTARGET_ARCH=%s\nTARGET_2ND_ARCH=%s\n' \
  "$(get_build_var TARGET_PRODUCT)" "$(get_build_var TARGET_ARCH)" "$(get_build_var TARGET_2ND_ARCH)" \
  | tee "$EVIDENCE/product-architecture-$LABEL.txt"
[[ "$(get_build_var TARGET_PRODUCT)" == "apollo_p1" ]] || { echo "Unexpected product" >&2; exit 1; }
ARCH="$(get_build_var TARGET_ARCH)"
SECOND="$(get_build_var TARGET_2ND_ARCH)"
[[ "$ARCH" == "arm" || "$SECOND" == "arm" ]] || { echo "NO_GO: product has no ARM32 ABI" >&2; exit 1; }
# Baseline public BSP module build (S9 source transforms are NOT auto-applied).
# pipefail preserves the build exit code.
# Record build start so a pre-existing installed artifact cannot be mistaken
# for one created by this command.
STAMP="$EVIDENCE/build-start-$LABEL.stamp"
touch "$STAMP"
m libbluetooth -j2 2>&1 | tee "$EVIDENCE/soong-libbluetooth-$LABEL.log"
PRODUCT_OUT="$(get_build_var PRODUCT_OUT)"
OUT32="$PRODUCT_OUT/system/lib/libbluetooth.so"
if [[ ! -f "$OUT32" || ! "$OUT32" -nt "$STAMP" ]]; then
  echo "NO_GO: ARM32 product system/lib/libbluetooth.so not produced: $OUT32" >&2
  exit 1
fi
cp "$OUT32" "$EVIDENCE/libbluetooth-arm32-$LABEL.so"
file "$EVIDENCE/libbluetooth-arm32-$LABEL.so" | tee "$EVIDENCE/file-$LABEL.txt"
readelf -h -d -Ws "$EVIDENCE/libbluetooth-arm32-$LABEL.so" > "$EVIDENCE/readelf-$LABEL.txt"
sha256sum "$EVIDENCE/libbluetooth-arm32-$LABEL.so" | tee "$EVIDENCE/sha256-$LABEL.txt"
readelf -h "$EVIDENCE/libbluetooth-arm32-$LABEL.so" | grep -q 'Class: *ELF32'
readelf -h "$EVIDENCE/libbluetooth-arm32-$LABEL.so" | grep -q 'Machine: *ARM'
echo "PASS: offline $LABEL ELF32 ARM libbluetooth output captured; OEM ABI NOT verified"
