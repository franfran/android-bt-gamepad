#!/usr/bin/env python3
"""Original M3 2024 ELF mini-debug plugin-symbol triage, strictly OFFLINE.

Original proprietary ELF is NEVER uploaded, loaded, executed, disassembled or
logged. Uses a private 0700 temporary directory only for decompressed mini-ELF.
Returns an allowlisted candidate symbol summary, not a verified loader/callsite.
"""
import argparse
import hashlib
import json
import lzma
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

SHA_2024 = "4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85"
BUILD_ID_2024 = "0d29a62178e43066e018216c1f1d5b18"
MAX_ELF = 40 * 1024 * 1024
MAX_DEBUG = 16 * 1024 * 1024
EXACT_SYMBOLS = (
    "dlopen", "android_dlopen_ext", "dlsym", "dlclose",
    "get_profile_interface", "btif_hh_get_interface", "hidh_conn_reg",
    "hidh_l2cif_connect_ind", "btm_sec_mx_access_request",
    "interop_database_add", "BTM_SecAddDevice",
)
CANDIDATE_RE = re.compile(r"(?i)(?:plugin|addon|extension|register_?profile|load_?module)")


def section(data, name):
    if len(data) < 52 or data[:4] != b"\x7fELF" or data[4:6] != b"\x01\x01":
        raise ValueError("expected 32-bit little-endian ELF")
    if struct.unpack_from("<H", data, 18)[0] != 40:
        raise ValueError("expected ARM machine")
    shoff = struct.unpack_from("<I", data, 32)[0]
    entsize, count, names_idx = struct.unpack_from("<HHH", data, 46)
    if entsize != 40 or not 2 <= count <= 2048 or names_idx >= count:
        raise ValueError("unsupported/missing ELF section header table")
    if shoff < 52 or shoff + count * entsize > len(data):
        raise ValueError("invalid section bounds")
    headers = [struct.unpack_from("<10I", data, shoff + 40 * i) for i in range(count)]
    noff, nsize = headers[names_idx][4:6]
    if noff + nsize > len(data) or nsize > 2 * 1024 * 1024:
        raise ValueError("invalid section name table")
    names = data[noff:noff+nsize]
    for sh in headers:
        ix = sh[0]
        if ix >= len(names):
            raise ValueError("bad section name index")
        end = names.find(b"\0", ix)
        if end < 0:
            raise ValueError("unterminated section name")
        if names[ix:end] == name.encode():
            off, size = sh[4:6]
            if size > MAX_ELF or off + size > len(data):
                raise ValueError("section outside ELF or too large")
            return data[off:off+size]
    raise ValueError("no original .gnu_debugdata section")


def unpack_minidebug(xz):
    decomp = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
    result = decomp.decompress(xz, max_length=MAX_DEBUG+1)
    if len(result) > MAX_DEBUG or not decomp.eof or decomp.unused_data:
        raise ValueError("unbounded, truncated or trailing mini-debug")
    if len(result) < 52 or not result.startswith(b"\x7fELF"):
        raise ValueError("mini-debug is not ELF")
    return result


def allowed_symbol_evidence(readelf_symbols):
    defined = set()
    for line in readelf_symbols.splitlines():
        fields = line.split()
        if len(fields) < 8 or not fields[0].rstrip(":").isdigit() or fields[6] == "UND":
            continue
        defined.add(fields[7].split("@", 1)[0])
    return {
        "exact_allowlisted_defined_symbols": sorted(defined.intersection(EXACT_SYMBOLS)),
        "other_symbol_names_with_plugin_like_tokens_count": sum(
            bool(CANDIDATE_RE.search(name)) for name in defined if name not in EXACT_SYMBOLS),
    }


def run_readelf(data):
    with tempfile.TemporaryDirectory(prefix="retrobox_oem_private_") as directory:
        file = Path(directory) / "mini-debug.elf"
        fd = os.open(file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        result = subprocess.run(["readelf", "-Ws", str(file)], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True, errors="replace",
                                timeout=20, check=False)
        if result.returncode:
            raise ValueError("readelf failed on private mini-debug")
        return result.stdout


def audit(original, expected_sha=SHA_2024):
    if original.is_symlink() or not original.is_file() or original.stat().st_size > MAX_ELF:
        raise ValueError("regular private ELF required")
    data = original.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError("original SHA mismatch")
    note = subprocess.run(["readelf", "-n", str(original)], stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, text=True, errors="replace",
                          timeout=20, check=False)
    if note.returncode or BUILD_ID_2024 not in note.stdout.lower():
        raise ValueError("original OEM Build ID mismatch")
    mini = unpack_minidebug(section(data, ".gnu_debugdata"))
    return {
        "original_2024_sha_verified": True,
        "original_2024_build_id_verified": True,
        "mini_debug_extracted_and_parsed": True,
        "symbol_triage": allowed_symbol_evidence(run_readelf(mini)),
        "decision": "UNRESOLVED_NEEDS_ACTUAL_CALLSITE_AND_FULL_MULTIGATE_ABI",
        "limits": [
            "defined symbol presence is NOT proof of real OEM runtime loader/callsite",
            "no matching symbol is NOT proof of no hidden/stripped/indirect loader",
            "plugin-looking symbols may be unrelated to Bluetooth HID Host",
            "only original libbluetooth.so inspected, not JNI/APK/vendor HAL",
            "no security policy, callbacks, Java bond, UHID or unloading is proven",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_2024_libbluetooth", type=Path)
    args = parser.parse_args()
    try:
        report = audit(args.original_2024_libbluetooth)
    except (OSError, ValueError, subprocess.TimeoutExpired, lzma.LZMAError) as e:
        print("NO_AUDIT: " + type(e).__name__ + " (private paths and contents withheld)",
              file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
