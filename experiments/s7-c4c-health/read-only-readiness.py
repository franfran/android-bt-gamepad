#!/usr/bin/env python3
"""Wi-Fi-first, read-only recovery readiness snapshot; NEVER restarts Bluetooth.

Run on the Mac with an explicit ADB serial. Prints sanitized JSON without
serials/PIDs/addresses. USB enumerated separately is fallback, not exercised.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("c4c_health", HERE / "read-only-health.py")
HEALTH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HEALTH)


def adb_inventory():
    proc = subprocess.run(["adb", "devices", "-l"], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=10)
    if proc.returncode or len(proc.stdout) > 65536:
        raise RuntimeError("ADB inventory unavailable")
    inventory = {}
    for line in proc.stdout.decode("utf-8", errors="replace").splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            inventory[parts[0]] = parts[1]
    return inventory


def readiness(serial):
    if not serial or len(serial) > 128 or serial.startswith("-"):
        raise ValueError("invalid explicit ADB serial")
    inventory = adb_inventory()
    if inventory.get(serial) != "device":
        raise RuntimeError("selected ADB transport is not ready")
    # No reboot, kill, attach, setprop, write, root shell changes or recovery.
    baseline = HEALTH.collect(serial)
    if not baseline["identity_verified"] or not baseline["tracer_absent"]:
        raise RuntimeError("Bluetooth read-only baseline invalid")
    transport = "wifi_adb" if ":" in serial else "usb_or_local_adb"
    # No sensitive transport ID or second device identity is returned.
    return {
        "stage": "S7-C4C-3",
        "mode": "READ_ONLY_RECOVERY_READINESS",
        "primary_transport": transport,
        "primary_transport_ready_now": True,
        "bluetooth_baseline_verified": True,
        "bluetooth_threads": baseline["threads"],
        "alternate_adb_device_enumerated": any(
            candidate != serial and state == "device"
            for candidate, state in inventory.items()),
        "usb_fallback_owner_confirmed": "REPORTED_SEPARATELY",
        "transport_survival_during_bluetooth_failure": "UNVERIFIED",
        "bluetooth_service_restart_verified": False,
        "linker_namespace_acceptance": "UNVERIFIED",
        "injection_authorized": False,
        "recovery_action_executed": False,
        "decision": "NO_GO",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adb_serial", help="explicit ADB serial; do not publish it")
    args = parser.parse_args(argv)
    try:
        report = readiness(args.adb_serial)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired, OSError) as exc:
        report = {
            "stage": "S7-C4C-3",
            "mode": "READ_ONLY_RECOVERY_READINESS",
            "decision": "NO_GO",
            "recovery_action_executed": False,
            "injection_authorized": False,
            "error": str(exc),
        }
        print(json.dumps(report, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
