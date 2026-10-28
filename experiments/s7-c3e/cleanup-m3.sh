#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
# Only files uploaded by this stage. Never touches any Bluetooth process.
adb -s "$DEVICE" shell 'rm -rf /data/local/tmp/retrobox_stage3d_s7c3e'
echo 'S7-C3e files removed.'
