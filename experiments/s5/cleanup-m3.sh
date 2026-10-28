#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
adb -s "$DEVICE" shell 'rm -rf /data/local/tmp/retrobox_stage3d_s5'
echo 'Removed S5 test files only; no Bluetooth service changes.'
