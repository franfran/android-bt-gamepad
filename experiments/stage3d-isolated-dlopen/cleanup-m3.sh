#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
# Deletes only D2b-2c staging directory. Never touches Bluetooth or older probes.
adb -s "$DEVICE" shell 'rm -rf /data/local/tmp/retrobox_stage3d_d2b2c'
echo 'Removed only /data/local/tmp/retrobox_stage3d_d2b2c'
