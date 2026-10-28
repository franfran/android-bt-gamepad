#!/bin/sh
set -eu
DEVICE="${1:?Usage: ./cleanup-m3.sh 192.0.2.10:1080}"
adb -s "$DEVICE" shell su 0 rm -f /data/local/tmp/retrobox_stage3d_d2b2b/ptrace_memory_probe
printf 'Removed Stage D2b-2b prerequisite binary only. Other stages untouched.\n'
