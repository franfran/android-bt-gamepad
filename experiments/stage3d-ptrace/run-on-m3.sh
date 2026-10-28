#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
HERE="$(cd "$(dirname "$0")" && pwd)"
DST=/data/local/tmp/retrobox_stage3d_d2b2
adb -s "$DEVICE" shell mkdir -p "$DST"
adb -s "$DEVICE" push "$HERE/ptrace_child_probe" "$DST/ptrace_child_probe"
adb -s "$DEVICE" shell chmod 755 "$DST/ptrace_child_probe"
echo '===== ISOLATED PTRACE TEST (NO BLUETOOTH PID) ====='
# Android shell timeout prevents indefinite waits; child may require manual cleanup if killed abruptly.
adb -s "$DEVICE" shell su 0 /system/bin/timeout 10 "$DST/ptrace_child_probe"
