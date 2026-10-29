#!/usr/bin/env python3
"""C4C-3 read-only Android linkerconfig *static* evidence; never executes in Bluetooth."""
import argparse
import json
import re
import subprocess
import sys

CANDIDATES = (
    "/linkerconfig/ld.config.txt",
    "/linkerconfig/com.android.bluetooth/ld.config.txt",
)
MAX_BYTES = 512 * 1024


def read_static(serial, path):
    if path not in CANDIDATES:
        raise ValueError("unapproved static path")
    p = subprocess.run(["adb", "-s", serial, "exec-out", "su", "0", "sh", "-c",
                        "cat " + path], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=12)
    if p.returncode:
        return None
    if len(p.stdout) > MAX_BYTES:
        raise RuntimeError("configuration exceeds bounded size")
    return p.stdout.decode("utf-8", "replace")


def summarize(text):
    sections = set()
    keys = set()
    mapped = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if re.fullmatch(r"\[[A-Za-z0-9_.-]{1,100}\]", line):
            sections.add(line[1:-1])
        elif "=" in line:
            key, value = (item.strip() for item in line.split("=", 1))
            # Only publish a predefined key category, not raw policy or paths.
            if re.fullmatch(r"dir\.[A-Za-z0-9_.-]{1,100}", key):
                keys.add("directory_section_mapping")
                if value:
                    mapped = True
            elif re.fullmatch(r"namespace\.[A-Za-z0-9_.-]+\.(?:isolated|search.paths|permitted.paths|links|visible|link\.[A-Za-z0-9_.-]+\.shared_libs)", key):
                keys.add("namespace_policy")
    return {"has_sections": bool(sections),
            "has_directory_section_mapping": mapped,
            "has_namespace_policy_keys": "namespace_policy" in keys,
            "policy_section_count": len(sections)}


def inspect(serial):
    if not serial or len(serial) > 128 or serial.startswith("-"):
        raise ValueError("invalid explicit ADB serial")
    found = []
    for path in CANDIDATES:
        data = read_static(serial, path)
        if data is not None:
            found.append(summarize(data))
    return {
        "stage": "S7-C4C-3",
        "mode": "READ_ONLY_STATIC_LINKERCONFIG",
        "candidate_files_read": len(found),
        "any_sections_found": any(x["has_sections"] for x in found),
        "any_directory_mapping_found": any(x["has_directory_section_mapping"] for x in found),
        "any_namespace_keys_found": any(x["has_namespace_policy_keys"] for x in found),
        "policy_inputs_observed": bool(found),
        "bluetooth_process_namespace_selected": "UNVERIFIED",
        "addon_path_permitted": "UNVERIFIED",
        "linker_namespace_acceptance": "UNVERIFIED",
        "injection_authorized": False,
        "decision": "NO_GO",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adb_serial")
    args = parser.parse_args(argv)
    try:
        result = inspect(args.adb_serial)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired, OSError):
        result = {"stage": "S7-C4C-3", "mode": "READ_ONLY_STATIC_LINKERCONFIG",
                  "decision": "NO_GO", "injection_authorized": False,
                  "error": "static evidence read failed"}
        print(json.dumps(result, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
