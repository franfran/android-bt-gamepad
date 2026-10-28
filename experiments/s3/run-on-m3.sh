#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="$HERE/safety_s3_arm32"
DIR='/data/local/tmp/retrobox_stage3d_safety_s3'
[[ -f "$BIN" ]] || { echo 'Missing prebuilt ARM32 binary' >&2; exit 2; }
command -v adb >/dev/null || { echo 'adb not installed' >&2; exit 2; }
adb -s "$DEVICE" get-state >/dev/null
adb -s "$DEVICE" shell "mkdir -p '$DIR'"
adb -s "$DEVICE" push "$BIN" "$DIR/safety_s3_arm32"
adb -s "$DEVICE" shell "chmod 755 '$DIR/safety_s3_arm32'"
echo '===== STAGE 3D S3 — ISOLATED SCRATCH MEMORY SAFETY ====='
echo 'Only an owned fork child. NO Bluetooth, no dlopen, no system changes.'
adb -s "$DEVICE" shell "$DIR/safety_s3_arm32"
