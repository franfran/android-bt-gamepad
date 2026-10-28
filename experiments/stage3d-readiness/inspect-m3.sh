#!/bin/sh
# RetroBox Stage 3D D2b passive process-inspection only. No ptrace or injection.
set -eu
DEVICE="${1:-192.0.2.10:1080}"
OUT="${2:-retrobox-d2b-readiness.txt}"
ADB="${ADB:-adb}"
PID=$("$ADB" -s "$DEVICE" shell pidof com.android.bluetooth | tr -d '\r' | awk '{print $1}')
if [ -z "$PID" ]; then echo 'Bluetooth process not found' >&2; exit 1; fi
{
  echo '===== RETROBOX D2b READINESS (READ-ONLY) ====='
  echo "PID=$PID"
  echo '===== DEVICE BUILD / POLICY ====='
  "$ADB" -s "$DEVICE" shell 'getprop ro.build.version.sdk; getenforce; getprop ro.debuggable; getprop ro.secure'
  echo '===== PROCESS STATUS (selected fields) ====='
  "$ADB" -s "$DEVICE" shell "su 0 cat /proc/$PID/status" | grep -E '^(Name|State|Tgid|Pid|PPid|TracerPid|Uid|Gid|NoNewPrivs|Seccomp|Cap(Inh|Prm|Eff|Bnd)):' || true
  echo '===== PROCESS SECURITY CONTEXT ====='
  "$ADB" -s "$DEVICE" shell "su 0 cat /proc/$PID/attr/current"
  echo '===== BLUETOOTH NATIVE MAPS ====='
  "$ADB" -s "$DEVICE" shell "su 0 cat /proc/$PID/maps" | grep -E '/system/lib/libbluetooth(_jni)?\.so|/apex/com.android.runtime/bin/linker' || true
  echo '===== LINKER CONFIG LOCATIONS ====='
  "$ADB" -s "$DEVICE" shell 'ls -l /linkerconfig/ld.config.txt /system/etc/ld.config.txt 2>/dev/null' || true
  echo '===== CURRENT STAGE 3D FILES ====='
  "$ADB" -s "$DEVICE" shell 'su 0 ls -l /data/local/tmp/retrobox_stage3d/ 2>/dev/null' || true
  echo '===== KERNEL PTRACE POLICY (if present) ====='
  "$ADB" -s "$DEVICE" shell 'cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || true'
  echo '===== END ====='
} | tee "$OUT"
echo "Saved: $OUT"
echo 'No process was attached, interrupted, injected, or modified.'
