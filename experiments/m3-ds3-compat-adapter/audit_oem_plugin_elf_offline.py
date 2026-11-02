#!/usr/bin/env python3
"""Fail-closed, read-only OEM M3 ELF loader-surface inventory.

This tool reports only allowlisted loader-related ELF evidence. It NEVER emits
raw strings, MACs, PINs, LinkKeys, disassembly or proprietary code to stdout.
It does not attach, execute binaries, load shared libraries, or touch Android.

Offline audit only, NOT a proof that a plugin works or does not exist.
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

OEM_2024_SHA256 = "4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85"
OEM_2024_BUILD_ID = "0d29a62178e43066e018216c1f1d5b18"
MAX_ELF_BYTES = 40 * 1024 * 1024
LOADER_SYMBOLS = (
    "dlopen", "dlsym", "dlclose", "dlerror", "android_dlopen_ext",
    "__loader_dlopen", "__loader_android_dlopen_ext",
    "android_get_exported_namespace", "android_create_namespace",
    "android_link_namespaces", "hw_get_module", "AServiceManager_getService",
    "AServiceManager_checkService", "AIBinder_getService",
)
KNOWN_INTERFACE_SYMBOLS = (
    "BLUETOOTH_VENDOR_LIB_INTERFACE",
    "HAL_MODULE_INFO_SYM",
    "bluetoothInterface",
    "bluetooth_module",
    "btif_hh_get_interface",
    "get_profile_interface",
)
# This is metadata-only. Library basenames are retained, never full paths.
LIBRARY_BASENAME = re.compile(r"(?<![A-Za-z0-9_])lib[A-Za-z0-9_.+-]{1,80}\.so(?![A-Za-z0-9_.+-])")


def elf_arm32_header(data):
    """Strict header validation before invoking host binutils."""
    if len(data) < 52 or data[:4] != b"\x7fELF":
        raise ValueError("not ELF")
    if data[4] != 1:
        raise ValueError("ELFCLASS32 is required")
    if data[5] != 1:
        raise ValueError("little-endian ARM ELF is required")
    machine = struct.unpack_from("<H", data, 18)[0]
    if machine != 40:
        raise ValueError("ELF e_machine must be ARM")
    return {"class": "ELF32", "endian": "little", "machine": "ARM"}


def parse_dynamic(output):
    needed = []
    sonames = []
    for line in output.splitlines():
        m = re.search(r"\(NEEDED\).*Shared library: \[([^\]]{1,120})\]", line)
        if m and re.fullmatch(r"[A-Za-z0-9_.+-]{1,120}", m.group(1)):
            needed.append(m.group(1))
        m = re.search(r"\(SONAME\).*Library soname: \[([^\]]{1,120})\]", line)
        if m and re.fullmatch(r"[A-Za-z0-9_.+-]{1,120}", m.group(1)):
            sonames.append(m.group(1))
    return sorted(set(needed)), sorted(set(sonames))


def parse_symbol_table(output):
    """Only return exact loader/interface symbol matches, never all symbols."""
    imported, defined = set(), set()
    allow = set(LOADER_SYMBOLS) | set(KNOWN_INTERFACE_SYMBOLS)
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 8 or not parts[0].rstrip(":").isdigit():
            continue
        # readelf -Ws: Num: Value Size Type Bind Vis Ndx Name
        name = parts[7].split("@", 1)[0]
        if name not in allow:
            continue
        if parts[6] == "UND":
            imported.add(name)
        else:
            defined.add(name)
    return sorted(imported), sorted(defined)


def parse_build_id(output):
    matches = re.findall(r"Build ID:\s*([0-9A-Fa-f]{8,128})", output)
    return sorted(set(x.lower() for x in matches))


def find_library_mentions(raw_text):
    # Input is output from "strings -a -n 6"; never output complete strings.
    return sorted(set(LIBRARY_BASENAME.findall(raw_text)))


def run_binutil(binary, command, timeout=15):
    result = subprocess.run(
        [command, *binary], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        timeout=timeout, check=False, text=True, errors="replace",
    )
    if result.returncode:
        raise RuntimeError("host binutils inspection failed")
    return result.stdout


def audit(elf_path, expected_sha):
    if not elf_path.is_file() or elf_path.is_symlink():
        raise ValueError("a regular local ELF is required")
    if elf_path.stat().st_size > MAX_ELF_BYTES:
        raise ValueError("ELF exceeds 40MiB limit")
    data = elf_path.read_bytes()
    ident = elf_arm32_header(data)
    sha = hashlib.sha256(data).hexdigest()
    if sha != expected_sha.lower():
        raise ValueError("OEM SHA-256 mismatch: refusing to attribute this ELF")
    if not shutil.which("readelf") or not shutil.which("strings"):
        raise RuntimeError("readelf and strings are required")
    dyn = run_binutil([str(elf_path), "-d"], "readelf")
    syms = run_binutil([str(elf_path), "-Ws"], "readelf")
    notes = run_binutil([str(elf_path), "-n"], "readelf")
    strs = run_binutil(["-a", "-n", "6", str(elf_path)], "strings")
    needed, sonames = parse_dynamic(dyn)
    imported, defined = parse_symbol_table(syms)
    ids = parse_build_id(notes)
    if not ids or OEM_2024_BUILD_ID not in ids:
        raise ValueError("original 2024 OEM build-id mismatch (not attributed)")
    library_mentions = find_library_mentions(strs)
    return {
        "evidence_kind": "read-only static ELF metadata; no callsite proof",
        "sha256_verified": True,
        "known_oem_2024_build_id_verified": True,
        "elf": ident,
        "needed_library_basenames": needed,
        "sonames": sonames,
        "allowlisted_undefined_loader_symbols": imported,
        "allowlisted_defined_symbols": defined,
        "embedded_library_basename_mentions": library_mentions,
        "limits": [
            "NEEDED library is a dependency, not a plugin",
            "embedded .so filename is a string, not dlopen-callsite proof",
            "imported dlopen/dlsym does not prove execution or approved ABI",
            "no loader import in dynamic symbols cannot prove absence of internal loading",
            "a supported loader alone does not grant HID/BTM, Java, or UHID callbacks",
            "this tool does not inspect OEM JNI/APK, vendor HAL or hidden OEM code",
        ],
        "plugin_decision": "UNRESOLVED: inspect actual load callsites and OEM callback ABI",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_oem_elf", type=Path)
    parser.add_argument("--expected-sha256", default=OEM_2024_SHA256)
    args = parser.parse_args()
    if not re.fullmatch("[0-9a-fA-F]{64}", args.expected_sha256):
        print("NO_GO: invalid expected SHA-256", file=sys.stderr)
        return 2
    try:
        result = audit(args.original_oem_elf, args.expected_sha256)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        # Do not print untrusted device strings, paths or stderr from tools.
        print("NO_GO: " + type(exc).__name__ + ": " + str(exc)[:140], file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
