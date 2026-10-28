#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
if [[ "${2:-preflight}" != preflight ]]; then
  echo 'Read-only preflight only; injection is deliberately disabled.' >&2
  exit 2
fi
adb -s "$DEVICE" get-state >/dev/null
PID=$(adb -s "$DEVICE" shell pidof com.android.bluetooth | tr -d '\r\n')
[[ "$PID" =~ ^[0-9]+$ ]] || { echo 'Bluetooth PID lookup failed' >&2; exit 3; }
DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LOG="$DIR/d2b-2d-b-linker-preflight.txt"
{
  echo '=== RetroBox D2b-2d-B linker preflight v2 (READ-ONLY) ==='
  echo "Device: $DEVICE"
  echo "Bluetooth PID: $PID"
  echo '--- Android release / ABI / SELinux ---'
  adb -s "$DEVICE" shell getprop ro.build.version.sdk
  adb -s "$DEVICE" shell getprop ro.product.cpu.abi
  adb -s "$DEVICE" shell su 0 getenforce
  echo '--- Target process name, uid, tracer, seccomp ---'
  adb -s "$DEVICE" shell "su 0 cat /proc/$PID/comm"
  adb -s "$DEVICE" shell "su 0 cat /proc/$PID/status" | grep -E '^(Name|State|Tgid|Pid|PPid|TracerPid|Uid|Gid|Threads|Seccomp):' || true
  echo '--- Target mappings: libdl, libc, linker, libbluetooth, addon ---'
  adb -s "$DEVICE" shell "su 0 cat /proc/$PID/maps" | grep -E '/(libdl|libc|linker|libbluetooth)(\.so)?([[:space:]]|$)|libretrobox_ds3_addon\.so' || true
  echo '--- This probe program mappings, for comparison (shell executable) ---'
  adb -s "$DEVICE" shell 'su 0 sh -c "cat /proc/self/maps"' | grep -E '/(libdl|libc|linker)(\.so)?([[:space:]]|$)' || true
  echo '--- Android linker namespace config mentions ---'
  adb -s "$DEVICE" shell 'su 0 ls -l /linkerconfig/ld.config.txt /apex/com.android.runtime/lib/bionic/libdl.so /system/lib/libdl.so /apex/com.android.runtime/bin/linker 2>&1' || true
  echo '--- Device Bluetooth alive ---'
  NEXT_PID=$(adb -s "$DEVICE" shell pidof com.android.bluetooth | tr -d '\r\n' || true)
  echo "Bluetooth PID after: ${NEXT_PID:-NOT RUNNING}"
  if [[ "$NEXT_PID" == "$PID" ]]; then echo 'PASS: same PID, read-only inspection completed'; else echo 'WARNING: process changed during inspection'; fi
  echo '--- Injection remains DISABLED ---'
} | tee "$LOG"
echo "Saved: $LOG"
