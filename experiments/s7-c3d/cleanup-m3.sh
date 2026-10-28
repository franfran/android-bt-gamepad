#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
# This only deletes S7-C3d test files; it does not stop or touch Bluetooth.
adb -s "$DEVICE" shell "rm -rf /data/local/tmp/retrobox_stage3d_s7c3d"
