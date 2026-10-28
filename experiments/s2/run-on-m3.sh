#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="$HERE/safety_s2_arm32"
DIR='/data/local/tmp/retrobox_stage3d_safety_s2'
if [[ ! -f "$BIN" ]]; then echo "Missing prebuilt binary" >&2; exit 2; fi
command -v adb >/dev/null || { echo 'adb not found' >&2; exit 2; }
adb -s "$DEVICE" get-state >/dev/null
adb -s "$DEVICE" shell "mkdir -p '$DIR'"
adb -s "$DEVICE" push "$BIN" "$DIR/safety_s2_arm32"
adb -s "$DEVICE" shell "chmod 755 '$DIR/safety_s2_arm32'"
echo '===== STAGE 3D S2 — ISOLATED BOUNDED REMOTE CALL ====='
echo 'Only own child. NO Bluetooth attach, system modifications or dlopen.'
adb -s "$DEVICE" shell "$DIR/safety_s2_arm32"
