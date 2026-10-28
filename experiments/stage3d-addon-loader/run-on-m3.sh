#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
BASE=/data/local/tmp/retrobox_stage3d
DIR="$(cd "$(dirname "$0")" && pwd)"
echo 'Stage 3D isolated loader test; no Bluetooth process injection.'
adb -s "$DEVICE" shell su 0 mkdir -p "$BASE"
adb -s "$DEVICE" push "$DIR/libretrobox_ds3_addon.so" "$BASE/libretrobox_ds3_addon.so"
adb -s "$DEVICE" push "$DIR/retrobox_loader" "$BASE/retrobox_loader"
adb -s "$DEVICE" shell su 0 chmod 755 "$BASE/retrobox_loader" "$BASE/libretrobox_ds3_addon.so"
echo '===== M3 RESULT ====='
adb -s "$DEVICE" shell su 0 "$BASE/retrobox_loader"
