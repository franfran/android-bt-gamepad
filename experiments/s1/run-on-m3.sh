#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="$HERE/safety_harness_arm32"
DIR='/data/local/tmp/retrobox_stage3d_safety_s1'
if [[ ! -f "$BIN" ]]; then echo "ERROR: prebuilt binary missing" >&2; exit 2; fi
command -v adb >/dev/null || { echo 'ERROR: adb not found' >&2; exit 2; }
adb -s "$DEVICE" get-state >/dev/null
adb -s "$DEVICE" shell "mkdir -p '$DIR'"
adb -s "$DEVICE" push "$BIN" "$DIR/safety_harness_arm32"
adb -s "$DEVICE" shell "chmod 755 '$DIR/safety_harness_arm32'"
echo '===== M3 ISOLATED MULTITHREAD SAFETY TEST (NO BLUETOOTH ATTACH) ====='
adb -s "$DEVICE" shell "$DIR/safety_harness_arm32"
