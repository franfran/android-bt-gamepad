#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
cd "$(dirname "$0")"
DEST=/data/local/tmp/retrobox_stage3d_s7c3e
printf '%s\n' '===== S7-C3e OWNED-PROCESS CONCURRENT DLOPEN =====' 'No Bluetooth attach, ptrace, injection or system writes.'
adb -s "$DEVICE" shell "mkdir -p $DEST"
for f in s7c3e_arm32 slow_normal.so slow_stall.so fast.so; do adb -s "$DEVICE" push "$f" "$DEST/$f"; done
adb -s "$DEVICE" shell "chmod 700 $DEST/s7c3e_arm32; chmod 644 $DEST/*.so"
echo '===== M3 RESULT ====='
# Exec isolated binary; it creates and reaps ONLY its own child process.
adb -s "$DEVICE" shell "$DEST/s7c3e_arm32"
