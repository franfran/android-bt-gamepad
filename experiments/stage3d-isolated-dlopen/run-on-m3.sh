#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REMOTE=/data/local/tmp/retrobox_stage3d_d2b2c
printf '%s\n' '===== Stage 3D D2b-2c isolated REMOTE dlopen ====='
printf '%s\n' 'Uploads both binaries each run; does NOT depend on previous boots.'
adb -s "$DEVICE" get-state >/dev/null
adb -s "$DEVICE" shell "mkdir -p '$REMOTE' && chmod 755 '$REMOTE'"
adb -s "$DEVICE" push "$HERE/remote_dlopen_fork" "$REMOTE/remote_dlopen_fork"
adb -s "$DEVICE" push "$HERE/libretrobox_ds3_addon.so" "$REMOTE/libretrobox_ds3_addon.so"
adb -s "$DEVICE" shell "chmod 755 '$REMOTE/remote_dlopen_fork' && chmod 644 '$REMOTE/libretrobox_ds3_addon.so'"
printf '%s\n' '===== M3 RESULT ====='
adb -s "$DEVICE" shell "$REMOTE/remote_dlopen_fork"
