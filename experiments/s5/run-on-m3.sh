#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REMOTE=/data/local/tmp/retrobox_stage3d_s5
command -v adb >/dev/null || { echo 'ERROR: adb is required'; exit 1; }
[ -f "$HERE/s5_arm32" ] && [ -f "$HERE/libretrobox_ds3_addon.so" ] || { echo 'ERROR: package missing binary/addon'; exit 1; }
echo '===== RETROBOX S5: ISOLATED MULTITHREAD REMOTE DLOPEN ====='
echo 'Fork-owned child ONLY. NEVER attaches Bluetooth. No persistent change.'
adb -s "$DEVICE" shell "mkdir -p '$REMOTE'"
adb -s "$DEVICE" push "$HERE/s5_arm32" "$REMOTE/s5_arm32"
adb -s "$DEVICE" push "$HERE/libretrobox_ds3_addon.so" "$REMOTE/libretrobox_ds3_addon.so"
adb -s "$DEVICE" shell "chmod 700 '$REMOTE/s5_arm32' && chmod 644 '$REMOTE/libretrobox_ds3_addon.so'"
echo '===== M3 RESULT ====='
# Timeout applies to ADB shell as well; child is fork-owned and the test has internal bounded remote-call wait.
if command -v timeout >/dev/null 2>&1; then
  timeout 12s adb -s "$DEVICE" shell "'$REMOTE/s5_arm32'"
else
  adb -s "$DEVICE" shell "'$REMOTE/s5_arm32'"
fi
