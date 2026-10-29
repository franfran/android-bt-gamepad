#!/usr/bin/env python3
"""Bounded read-only Bluetooth health snapshot for owner-controlled M3.

Never attaches, stops, changes, or restarts the service. Prints sanitized
facts only; rejects PID changes. This is not linker namespace verification.
"""
import argparse
import json
import re
import subprocess
import sys

TIMEOUT = 12
MAX_BYTES = 512 * 1024
PROC_NAME = "com.android.bluetooth"
COMM = "droid.bluetooth"


def read(serial, command):
    # command is built exclusively from constants or validated decimal PID.
    args = ["adb", "-s", serial, "exec-out", "su", "0", "sh", "-c", command]
    proc = subprocess.run(args, capture_output=True, timeout=TIMEOUT)
    if proc.returncode:
        raise RuntimeError("read-only device command failed")
    if len(proc.stdout) > MAX_BYTES:
        raise RuntimeError("read-only response exceeds bounded size")
    return proc.stdout.decode("utf-8", errors="replace").replace("\r", "").replace("\x00", "")


def single_pid(value):
    value = value.strip()
    if not re.fullmatch(r"[1-9][0-9]{0,7}", value):
        raise ValueError("missing or ambiguous Bluetooth PID")
    return value


def field(status, name):
    match = re.search(r"^" + re.escape(name) + r":\s*([0-9]+)", status, re.M)
    if not match:
        raise ValueError("missing process status field: " + name)
    return int(match.group(1))


def collect(serial):
    if not serial or len(serial) > 128 or serial.startswith("-"):
        raise ValueError("invalid explicit ADB serial")
    first = single_pid(read(serial, "pidof " + PROC_NAME))
    comm = read(serial, "cat /proc/" + first + "/comm").strip()
    status = read(serial, "cat /proc/" + first + "/status")
    maps = read(serial, "cat /proc/" + first + "/maps")
    second = single_pid(read(serial, "pidof " + PROC_NAME))
    if first != second or comm != COMM:
        raise ValueError("target identity changed during read-only inspection")
    uid, threads, tracer = field(status, "Uid"), field(status, "Threads"), field(status, "TracerPid")
    if uid != 1002 or not 1 <= threads <= 512:
        raise ValueError("Bluetooth identity/thread validation failed")
    if tracer != 0:
        raise ValueError("Bluetooth already traced; abort")
    paths = [line.split()[-1] for line in maps.splitlines() if "/" in line and len(line.split()) >= 6]
    library = any(p == "/system/lib/libbluetooth.so" for p in paths)
    linker = any(p.endswith("/linker") or p.endswith("/linker32") for p in paths)
    bionic = any("/bionic/" in p and ("libdl.so" in p or "libc.so" in p) for p in paths)
    addon = any("libretrobox_ds3_addon.so" in p for p in paths)
    if not library:
        raise ValueError("expected Bluetooth library mapping missing")
    # No PID, paths, maps, MAC, address, tokens, or raw status output in JSON.
    return {
        "stage": "S7-C4C-3",
        "mode": "READ_ONLY_BLUETOOTH_HEALTH",
        "identity_verified": True,
        "uid_match": True,
        "threads": threads,
        "tracer_absent": True,
        "libbluetooth_mapped": library,
        "bionic_runtime_mapped": bionic,
        "linker_mapping_seen": linker,
        "addon_mapped": addon,
        "linker_namespace_acceptance": "UNVERIFIED",
        "independent_recovery": "UNVERIFIED",
        "injection_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adb_serial", help="explicit serial from adb devices -l")
    args = parser.parse_args(argv)
    try:
        report = collect(args.adb_serial)
    except (ValueError, RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
        print(json.dumps({"stage": "S7-C4C-3", "mode": "READ_ONLY_BLUETOOTH_HEALTH",
                          "status": "NO_GO", "error": str(exc),
                          "injection_authorized": False}), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
