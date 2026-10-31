#!/bin/sh
# Owner-initiated READ-ONLY original-M3 evidence collection.
# This script NEVER uploads anything, restarts Bluetooth, remounts partitions,
# changes settings, injects code or pairs devices.
# Usage: sh collect_m3_native_readonly.sh <explicit-adb-serial> [private-dir]
set -eu
umask 077

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  printf '%s\n' 'Usage: sh collect_m3_native_readonly.sh <ADB_SERIAL> [PRIVATE_OUTPUT_DIRECTORY]' >&2
  exit 2
fi
serial=$1
output=${2:-"$HOME/retrobox-private/m3-native"}
command -v adb >/dev/null 2>&1 || {
  printf '%s\n' 'adb not found. Install/configure platform-tools first.' >&2
  exit 1
}

# Require an explicit absolute location; never accidentally write under the
# current Git working directory when the operator uses a relative path.
case "$output" in
  /*) ;;
  *) printf '%s\\n' 'Private output directory must be an absolute path.' >&2; exit 2 ;;
esac

mkdir -p "$output"
# Refuse a repository-local output location: extracted OEM libraries must not
# accidentally become Git-tracked or shared in a pull request.
case "$output" in
  .|./*|*/android-bt-gamepad|*/android-bt-gamepad/*)
    printf '%s\n' 'Refusing repository-local output path; use a private directory outside Git.' >&2
    exit 2 ;;
esac

native="$output/m3-original-2024-libbluetooth.so"
if [ -e "$native" ] || [ -L "$native" ]; then
  printf '%s\n' "Refusing to overwrite existing file: $native" >&2
  exit 1
fi

# Only read the existing system library; adb shell or root are not required for
# normal /system/lib/ files. Exact remote file path is from original S7 maps.
printf '%s\n' 'Pulling original installed Bluetooth ELF (READ-ONLY on device).'
adb -s "$serial" pull /system/lib/libbluetooth.so "$native" || {
  rm -f "$native"
  printf '%s\n' 'ADB pull failed; no fallback to remount or su.' >&2
  exit 1
}
printf '%s\n' 'Offline SHA-256 fingerprint:'
if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 "$native"
elif command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$native"
else
  printf '%s\n' 'Install sha256sum or use shasum -a 256 to fingerprint offline.' >&2
fi

# Kernel config is optional; many OEM kernels omit /proc/config.gz.
# Capture only when accessible, and avoid retaining an empty/failure output.
cfg="$output/m3-kernel.config.gz"
if [ ! -e "$cfg" ] && [ ! -L "$cfg" ]; then
  if adb -s "$serial" exec-out cat /proc/config.gz > "$cfg" 2>/dev/null && [ -s "$cfg" ]; then
    printf '%s\n' "Saved optional kernel config: $cfg"
  else
    rm -f "$cfg"
    printf '%s\n' 'Kernel /proc/config.gz unavailable (non-fatal).'
  fi
fi

printf '%s\n' "Saved private native evidence: $native"
printf '%s\n' 'Do NOT commit vendor .so, kernel config, MAC addresses or raw Bluetooth logs to Git.'
