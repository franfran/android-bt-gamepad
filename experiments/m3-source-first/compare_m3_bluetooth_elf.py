#!/usr/bin/env python3
"""Offline Android ELF ABI gate for M3 libbluetooth (no device access).

Compares machine, SONAME, dynamic NEEDED and dynamic exported/undefined symbols.
Requires readelf; results describe differences, NOT deployment compatibility.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

OEM_SHA = "4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85"

def readelf(path, *args):
    p = subprocess.run(["readelf", *args, str(path)], text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(f"readelf failed on {path}: {p.stderr.strip()}")
    return p.stdout

def inspect(path):
    header = readelf(path, "-h")
    dynamic = readelf(path, "-d")
    symbols = readelf(path, "--dyn-syms", "--wide")
    klass = re.search(r"Class:\s+(\S+)", header)
    machine = re.search(r"Machine:\s+(.+)", header)
    soname = re.findall(r"\(SONAME\).*?\[(.*?)\]", dynamic)
    needed = sorted(re.findall(r"\(NEEDED\).*?\[(.*?)\]", dynamic))
    exported, imported = set(), set()
    for line in symbols.splitlines():
        # readelf --dyn-syms --wide: Num Value Size Type Bind Vis Ndx Name
        m = re.match(r"\s*\d+:\s+\S+\s+\d+\s+\S+\s+(GLOBAL|WEAK)\s+\S+\s+(\S+)\s+(\S+)", line)
        if m:
            bind, section, symbol = m.groups()
            if section == "UND":
                imported.add(symbol)
            else:
                exported.add(symbol)
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "class": klass.group(1) if klass else None,
        "machine": machine.group(1).strip() if machine else None,
        "soname": soname,
        "needed": needed,
        "exports": sorted(exported),
        "imports": sorted(imported),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("oem", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--json-output", type=Path)
    args = ap.parse_args()
    for p in [args.oem, args.candidate]:
        if not p.is_file():
            ap.error(f"missing: {p}")
    old, new = inspect(args.oem), inspect(args.candidate)
    differences = {}
    for field in ("class", "machine", "soname", "needed"):
        if old[field] != new[field]:
            differences[field] = {"oem": old[field], "candidate": new[field]}
    missing_exports = sorted(set(old["exports"]) - set(new["exports"]))
    added_imports = sorted(set(new["imports"]) - set(old["imports"]))
    report = {
        "oem_sha256_matches_record": old["sha256"] == OEM_SHA,
        "candidate_sha256": new["sha256"],
        "differences": differences,
        "missing_oem_exports": missing_exports,
        "candidate_new_imports": added_imports,
        "candidate_needed": new["needed"],
        "caveat": "Static ELF gate only; does not prove Android linker namespace, symbol versions, JNI runtime compatibility, or DS3 functionality",
    }
    if args.json_output:
        args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["oem_sha256_matches_record"]:
        print("NO_GO: original OEM ELF SHA256 mismatches archived evidence", file=sys.stderr)
        return 2
    if old["class"] != "ELF32" or "ARM" not in (old["machine"] or ""):
        print("NO_GO: unexpected OEM architecture", file=sys.stderr)
        return 2
    if new["class"] != "ELF32" or "ARM" not in (new["machine"] or ""):
        print("NO_GO: candidate is not ELF32 ARM", file=sys.stderr)
        return 2
    if differences or missing_exports:
        print("NO_GO: static ABI differences require investigation", file=sys.stderr)
        return 1
    print("Static ABI screen: no basic header/NEEDED/SONAME/export loss detected. NOT runtime verified.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
