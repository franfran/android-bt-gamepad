#!/usr/bin/env python3
"""C4C-3 read-only package/process identity corroboration; never loads code."""
import argparse
import json
import re
import subprocess
import sys

PACKAGE = "com.android.bluetooth"

def read(serial, cmd, root=False):
    prefix = ["adb", "-s", serial, "exec-out"]
    if root:
        prefix += ["su", "0", "sh", "-c"]
    args = prefix + [cmd] if root else prefix + cmd.split()
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12)
    if p.returncode or len(p.stdout) > 16384:
        raise RuntimeError("adb_read_failed")
    return p.stdout

def parse_pid(raw):
    value = raw.decode("utf-8", "replace").strip()
    if not re.fullmatch(r"[1-9][0-9]{0,7}", value):
        raise ValueError("missing or ambiguous process PID")
    return value

def parse_status(raw):
    text = raw.decode("utf-8", "replace")
    values = {}
    for field in ("Pid", "Uid", "TracerPid", "PPid"):
        match = re.search(r"^" + field + r":\s*(\d+)", text, re.M)
        if not match:
            raise ValueError("missing status field")
        values[field] = int(match.group(1))
    return values

def package_uid(raw):
    text = raw.decode("utf-8", "replace").replace("\r", "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    pattern = r"package:com\.android\.bluetooth\s+uid:(\d+)"
    if len(lines) != 1:
        raise ValueError("package_uid_format")
    match = re.fullmatch(pattern, lines[0])
    if not match:
        raise ValueError("package_uid_format")
    return int(match.group(1))

def cmdline_category(raw):
    # The cmdline is private. Only exact package-name evidence is reported.
    first = raw.split(b"\x00", 1)[0]
    if first == PACKAGE.encode("ascii"):
        return "EXACT_PACKAGE_PROCESS_NAME"
    if not first or len(first) > 512:
        return "UNKNOWN"
    return "OTHER_PROCESS_NAME"

def collect(serial):
    if not serial or len(serial) > 128 or serial.startswith("-"):
        raise ValueError("invalid serial")
    stage = "pid_lookup"
    first = parse_pid(read(serial, "pidof com.android.bluetooth", True))
    stage = "process_identity"
    status1 = parse_status(read(serial, "cat /proc/" + first + "/status", True))
    comm = read(serial, "cat /proc/" + first + "/comm", True).decode("utf-8", "replace").strip()
    if status1["Pid"] != int(first) or status1["Uid"] != 1002 or status1["TracerPid"] != 0 or comm != "droid.bluetooth":
        raise ValueError("Bluetooth process identity mismatch")
    stage = "process_cmdline"
    name = cmdline_category(read(serial, "cat /proc/" + first + "/cmdline", True))
    stage = "package_uid_lookup"
    try:
        uid = package_uid(read(serial, "pm list packages -U com.android.bluetooth"))
    except (ValueError, RuntimeError):
        raise ValueError("package_uid_lookup_unavailable")
    status2 = parse_status(read(serial, "cat /proc/" + first + "/status", True))
    if parse_pid(read(serial, "pidof com.android.bluetooth", True)) != first or status1 != status2:
        raise ValueError("Bluetooth process changed during inspection")
    uid_matches = uid == status1["Uid"]
    strong = uid_matches and name == "EXACT_PACKAGE_PROCESS_NAME"
    return {
        "stage": "S7-C4C-3",
        "mode": "READ_ONLY_PACKAGE_PROCESS_ASSOCIATION",
        "bluetooth_identity_verified": True,
        "package_uid_matches_process": uid_matches,
        "process_name_relation": name,
        "package_process_association": "CORROBORATED" if strong else "UNVERIFIED",
        "shared_uid_caveat": True,
        "apk_classloader_link": "UNVERIFIED",
        "caller_linker_namespace": "UNVERIFIED",
        "addon_path_permitted": "UNVERIFIED",
        "injection_authorized": False,
        "decision": "NO_GO",
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adb_serial")
    args = parser.parse_args(argv)
    try:
        report = collect(args.adb_serial)
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired):
        report = {"stage": "S7-C4C-3", "mode": "READ_ONLY_PACKAGE_PROCESS_ASSOCIATION",
                  "error": "read-only package/process lookup unavailable",
                  "injection_authorized": False, "decision": "NO_GO"}
        print(json.dumps(report, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
