#!/usr/bin/env python3
"""Offline-only M3 Bluetooth native/UHID compatibility audit (heuristic).
No device access, /dev/uhid writes, secrets or security decisions.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct

MARKERS = {
    "legacy_no_set_report_reply": b"UHID_SET_REPORT_REPLY not supported",
    "uhid_set_report_label": b"UHID_SET_REPORT",
    "uhid_device_path": b"/dev/uhid",
}
CONFIG_KEYS = ("CONFIG_HID", "CONFIG_UHID", "CONFIG_HID_SONY")


def native_summary(data: bytes, *, expected_sha256=None):
    digest = hashlib.sha256(data).hexdigest()
    if len(data) < 20 or data[:4] != b"\x7fELF":
        raise ValueError("input is not ELF")
    elf_class, endian = data[4:6]
    if (elf_class, endian) != (1, 1) or struct.unpack_from("<H", data, 18)[0] != 40:
        raise ValueError("not little-endian ELF32 ARM (M3 native ABI)")
    if expected_sha256 is not None and digest.lower() != expected_sha256.lower():
        raise ValueError("input ELF does not match expected SHA-256")
    present = {label: marker in data for label, marker in MARKERS.items()}
    return {
        "sha256": digest,
        "elf": "ELF32 ARM little-endian",
        "literal_markers": present,
        "result": "INCONCLUSIVE_BINARY_MARKERS_ONLY",
        "warning": ("A marker may reside in unreachable code; absent markers may be "
                    "stripped or worded differently. Determine actual compiled "
                    "UHID_SET_REPORT request/reply behavior by callgraph disassembly."),
    }


def kernel_config_summary(raw: bytes):
    if raw.startswith(b"\x1f\x8b"):
        raw = gzip.decompress(raw)
    config = raw.decode("utf-8", errors="replace")
    values = {}
    for key in CONFIG_KEYS:
        match = re.search(r"^" + re.escape(key) + r"=(y|m|n)$", config, re.M)
        unset = re.search(r"^# " + re.escape(key) + r" is not set$", config, re.M)
        values[key] = match.group(1) if match else ("n" if unset else "UNKNOWN")
    return {
        "config": values,
        "warning": ("A kernel config is not proof the active device is bound to "
                    "hid-sony over Bluetooth. USB binding is insufficient."),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--elf", type=Path, required=True, help="Private extracted libbluetooth.so")
    p.add_argument("--expected-sha256", help="Optional exact-firmware SHA pin")
    p.add_argument("--kernel-config", type=Path, help="Optional archived .config or config.gz")
    args = p.parse_args()
    result = {"native": native_summary(args.elf.read_bytes(), expected_sha256=args.expected_sha256)}
    if args.kernel_config:
        result["kernel"] = kernel_config_summary(args.kernel_config.read_bytes())
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
