#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REMOTE=/data/local/tmp/retrobox_stage3d_s7c1
command -v adb >/dev/null || { echo 'ERROR: adb not found'; exit 1; }
[[ -f "$HERE/s7c1_arm32" && -f "$HERE/libretrobox_ds3_addon.so" ]] || { echo 'ERROR: binary or addon missing'; exit 1; }
echo '===== S7-C1 ISOLATED LOADER INTEGRATION ====='
echo 'Owned child ONLY; no Bluetooth process attach or system library replacement.'
adb -s "$DEVICE" shell "mkdir -p '$REMOTE'"
adb -s "$DEVICE" push "$HERE/s7c1_arm32" "$REMOTE/s7c1_arm32"
adb -s "$DEVICE" push "$HERE/libretrobox_ds3_addon.so" "$REMOTE/libretrobox_ds3_addon.so"
adb -s "$DEVICE" shell "chmod 700 '$REMOTE/s7c1_arm32' && chmod 644 '$REMOTE/libretrobox_ds3_addon.so'"
echo '===== M3 RESULT ====='
if command -v timeout >/dev/null 2>&1; then
  timeout 15s adb -s "$DEVICE" shell "'$REMOTE/s7c1_arm32'"
else
  adb -s "$DEVICE" shell "'$REMOTE/s7c1_arm32'"
fi
