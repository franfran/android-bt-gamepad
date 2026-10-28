#!/bin/sh
set -eu
DEVICE="${1:?Usage: ./run-on-m3.sh 192.0.2.10:1080}"
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REMOTE=/data/local/tmp/retrobox_stage3d_d2b2b
adb -s "$DEVICE" shell mkdir -p "$REMOTE"
adb -s "$DEVICE" push "$HERE/ptrace_memory_probe" "$REMOTE/ptrace_memory_probe"
adb -s "$DEVICE" shell su 0 chmod 755 "$REMOTE/ptrace_memory_probe"
echo '===== M3 ISOLATED MEMORY TEST ====='
adb -s "$DEVICE" shell su 0 "$REMOTE/ptrace_memory_probe"
