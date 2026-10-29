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
    if not lines or len(lines) > 128:
        raise ValueError("package_uid_format")
    matches = []
    for line in lines:
        match = re.fullmatch(r"package:([A-Za-z0-9_.]+)\s+uid:(\d+)", line)
        if not match:
            raise ValueError("package_uid_format")
        if match.group(1) == PACKAGE:
            matches.append(int(match.group(2)))
    if len(matches) != 1:
        raise ValueError("package_uid_format")
    return matches[0]


def lookup_uid(serial):
    # Keep diagnostics as fixed categories, never raw PM output or stderr.
    outcomes = []
    attempts = (("pm list packages -U com.android.bluetooth", False),
                ("cmd package list packages -U com.android.bluetooth", False),
                ("cmd package list packages -U com.android.bluetooth", True))
    for command, root in attempts:
        try:
            data = read(serial, command, root)
        except (RuntimeError, OSError, subprocess.TimeoutExpired):
            outcomes.append("COMMAND_FAILED")
            continue
        try:
            return package_uid(data)
        except ValueError:
            outcomes.append("EMPTY_OUTPUT" if not data.strip() else "UNRECOGNIZED_FORMAT")
    raise RuntimeError("package_uid_unavailable:" + ",".join(outcomes))


def cmdline_category(raw):
    # The cmdline is private. Only exact package-name evidence is reported.
    first = raw.split(b"\x00", 1)[0]
    if first == PACKAGE.encode("ascii"):
        return "EXACT_PACKAGE_PROCESS_NAME"
    if not first or len(first) > 512:
        return "UNKNOWN"
    return "OTHER_PROCESS_NAME"

def safe_step(label, fn):
    try:
        return fn()
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired):
        raise RuntimeError("stage_" + label)


def collect(serial):
    if not serial or len(serial) > 128 or serial.startswith("-"):
        raise ValueError("invalid serial")
    first = safe_step("pid", lambda: parse_pid(read(serial, "pidof com.android.bluetooth", True)))
    status1 = safe_step("identity", lambda: parse_status(read(serial, "cat /proc/" + first + "/status", True)))
    comm = safe_step("identity", lambda: read(serial, "cat /proc/" + first + "/comm", True).decode("utf-8", "replace").strip())
    if status1["Pid"] != int(first) or status1["Uid"] != 1002 or status1["TracerPid"] != 0 or comm != "droid.bluetooth":
        raise RuntimeError("stage_identity")
    name = safe_step("cmdline", lambda: cmdline_category(read(serial, "cat /proc/" + first + "/cmdline", True)))
    try:
        uid = lookup_uid(serial)
    except RuntimeError as exc:
        if str(exc).startswith("package_uid_unavailable:"):
            raise RuntimeError("stage_package_uid|" + str(exc).split(":", 1)[1])
        raise RuntimeError("stage_package_uid")
    status2 = safe_step("revalidation", lambda: parse_status(read(serial, "cat /proc/" + first + "/status", True)))
    last = safe_step("revalidation", lambda: parse_pid(read(serial, "pidof com.android.bluetooth", True)))
    if last != first or status1 != status2:
        raise RuntimeError("stage_revalidation")
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
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        reason = str(exc)
        stage_name = reason.split("|", 1)[0]
        if stage_name not in ("stage_pid", "stage_identity", "stage_cmdline", "stage_package_uid", "stage_revalidation"):
            stage_name = "stage_other"
        report = {"stage": "S7-C4C-3", "mode": "READ_ONLY_PACKAGE_PROCESS_ASSOCIATION",
                  "error": "read-only package/process lookup unavailable",
                  "failure_stage": stage_name,
                  "package_uid_attempts": reason.split("|", 1)[1].split(",") if stage_name == "stage_package_uid" and "|" in reason else [],
                  "injection_authorized": False, "decision": "NO_GO"}
        print(json.dumps(report, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
