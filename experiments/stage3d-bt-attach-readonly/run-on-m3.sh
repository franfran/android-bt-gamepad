#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
HERE="$(cd "$(dirname "$0")" && pwd)"
REMOTE='/data/local/tmp/retrobox_stage3d_d2b2d_a'
command -v adb >/dev/null || { echo 'adb not found'; exit 1; }
echo '===== D2b-2d-A Bluetooth attach/detach: NO INJECTION ====='
echo 'The Bluetooth main thread may pause briefly. Do not run while using Bluetooth audio/controllers.'
adb -s "$DEVICE" shell "mkdir -p $REMOTE"
adb -s "$DEVICE" push "$HERE/bt_attach_probe" "$REMOTE/bt_attach_probe" >/dev/null
adb -s "$DEVICE" shell "chmod 755 $REMOTE/bt_attach_probe"
PID="$(adb -s "$DEVICE" shell pidof com.android.bluetooth | tr -d '\r\n')"
if [[ ! "$PID" =~ ^[0-9]+$ ]]; then echo "Invalid Bluetooth PID: $PID"; exit 2; fi
echo "Target PID=$PID"
echo '===== M3 RESULT ====='
set +e
adb -s "$DEVICE" shell "su 0 $REMOTE/bt_attach_probe $PID"
RC=$?
set -e
echo '===== POST-CHECK ====='
AFTER="$(adb -s "$DEVICE" shell pidof com.android.bluetooth | tr -d '\r\n' || true)"
echo "Bluetooth PID after: ${AFTER:-not running}"
adb -s "$DEVICE" shell "su 0 cat /proc/$PID/status" 2>/dev/null | grep -E '^(Name|State|TracerPid):' || echo 'Original process no longer present'
if [[ "$AFTER" != "$PID" ]]; then echo 'WARNING: Bluetooth PID changed or service stopped. A crash/restart may have occurred.'; exit 3; fi
if [[ "$RC" -ne 0 ]]; then echo "Probe returned nonzero: $RC (inspect logs)"; exit "$RC"; fi
echo 'Probe finished; confirm Bluetooth still works before any next stage.'
