#!/usr/bin/env python3
"""Read-only, sanitized Bluetooth APK partition classification for M3."""
import argparse
import json
import re
import subprocess
import sys

PREFIXES = (
    ("/system_ext/", "SYSTEM_EXT"),
    ("/system/", "SYSTEM"),
    ("/product/", "PRODUCT"),
    ("/vendor/", "VENDOR"),
    ("/odm/", "ODM"),
    ("/apex/", "APEX"),
    ("/data/app/", "DATA_APP"),
)
MAX_OUTPUT = 8192


def classify(raw):
    lines = [line.strip() for line in raw.replace("\r", "").splitlines() if line.strip()]
    if not lines or len(lines) > 16:
        raise ValueError("package paths missing or ambiguous")
    categories = set()
    for line in lines:
        if not line.startswith("package:"):
            raise ValueError("unexpected package path response")
        path = line[len("package:"):]
        if not path.endswith(".apk") or "\x00" in path or ".." in path.split("/"):
            raise ValueError("invalid package path")
        choices = [name for prefix, name in PREFIXES if path.startswith(prefix)]
        if len(choices) != 1:
            categories.add("UNKNOWN")
        else:
            categories.add(choices[0])
    return {
        "stage": "S7-C4C-3",
        "mode": "READ_ONLY_BLUETOOTH_APK_ORIGIN",
        "apk_paths_observed": len(lines),
        "apk_partition_categories": sorted(categories),
        "bluetooth_process_uses_this_package": "UNVERIFIED",
        "classloader_namespace": "UNVERIFIED",
        "native_dlopen_caller": "UNVERIFIED",
        "addon_path_permitted": "UNVERIFIED",
        "injection_authorized": False,
        "decision": "NO_GO",
    }


def collect(serial):
    if not serial or len(serial) > 128 or serial.startswith("-"):
        raise ValueError("invalid ADB serial")
    cmd = ["adb", "-s", serial, "exec-out", "pm", "path", "com.android.bluetooth"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12)
    if p.returncode or len(p.stdout) > MAX_OUTPUT:
        raise RuntimeError("read-only package lookup unavailable")
    return classify(p.stdout.decode("utf-8", errors="replace"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adb_serial")
    args = parser.parse_args(argv)
    try:
        result = collect(args.adb_serial)
    except (RuntimeError, ValueError, subprocess.TimeoutExpired, OSError):
        print(json.dumps({"stage": "S7-C4C-3",
                          "mode": "READ_ONLY_BLUETOOTH_APK_ORIGIN",
                          "error": "read-only package evidence unavailable",
                          "injection_authorized": False,
                          "decision": "NO_GO"}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
