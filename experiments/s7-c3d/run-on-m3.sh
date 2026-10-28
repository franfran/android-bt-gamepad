#!/usr/bin/env bash
set -euo pipefail
DEVICE="${1:-192.0.2.10:1080}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE=/data/local/tmp/retrobox_stage3d_s7c3d
command -v adb >/dev/null || { echo 'ERROR: adb not installed'; exit 1; }
for f in s7c3d_arm32 slow_normal.so slow_stall.so; do
  [[ -f "$HERE/$f" ]] || { echo "ERROR: missing $f"; exit 1; }
done
printf '%s\n' '===== S7-C3d: ISOLATED CONSTRUCTOR DELAY / FAIL-CLOSED =====' \
  'Owned fork child ONLY; NO Bluetooth attach, remote injection, or system modification.'
adb -s "$DEVICE" shell "mkdir -p '$REMOTE'"
for f in s7c3d_arm32 slow_normal.so slow_stall.so; do
 adb -s "$DEVICE" push "$HERE/$f" "$REMOTE/$f"
done
adb -s "$DEVICE" shell "chmod 700 '$REMOTE/s7c3d_arm32'; chmod 644 '$REMOTE/slow_normal.so' '$REMOTE/slow_stall.so'"
echo '===== M3 RESULT ====='
# Python provides a Mac-compatible host-side timeout; internal test deadlines are bounded too.
python3 - "$DEVICE" "$REMOTE" <<'PY'
import subprocess,sys
cmd=['adb','-s',sys.argv[1],'shell',sys.argv[2]+'/s7c3d_arm32']
try:
    r=subprocess.run(cmd, timeout=15)
except subprocess.TimeoutExpired:
    print('ERROR: host timeout. Check running owned test process before restarting.',file=sys.stderr)
    sys.exit(124)
sys.exit(r.returncode)
PY
