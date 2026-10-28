#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
adb -s "$DEVICE" shell rm -f /data/local/tmp/retrobox_stage3d_d2b2/ptrace_child_probe
adb -s "$DEVICE" shell rmdir /data/local/tmp/retrobox_stage3d_d2b2 2>/dev/null || true
