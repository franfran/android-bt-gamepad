#!/usr/bin/env python3
"""Apply S9 three-file experiment to a pinned, local BSP tree (offline only).

This is a workspace edit, not a deployable DS3 fix. Invoke only after baseline build.
No network calls, no device calls, no implicit overwrite of local modifications.
"""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("s9_source", HERE / "test_integrated_btif_allocation_source.py")
s9 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s9)

def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], text=True,
                          capture_output=True, check=True).stdout.strip()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bsp_root", type=Path)
    args = parser.parse_args()
    root = args.bsp_root.resolve()
    if git(root, "rev-parse", "HEAD") != s9.REV:
        raise SystemExit("NO_GO: BSP revision not pinned to S9 source")
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root:
        raise SystemExit("NO_GO: expected monorepo root")
    sources = {}
    for name, expected_sha in s9.FILES.items():
        relative = s9.BASE + name
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise SystemExit("NO_GO: absent/symlink source " + relative)
        # Both staged and unstaged changes are rejected for these paths.
        if git(root, "status", "--porcelain", "--", relative):
            raise SystemExit("NO_GO: source already modified " + relative)
        raw = path.read_bytes()
        digest = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if expected_sha and digest != expected_sha:
            raise SystemExit("NO_GO: mismatched pinned Git blob " + relative)
        sources[name] = raw.decode("utf-8")
    try:
        changed = s9.transform(dict(sources))
    except (AssertionError, ValueError) as error:
        raise SystemExit("NO_GO: S9 source anchor mismatch: " + str(error))
    for name, value in changed.items():
        if value == sources[name]:
            raise SystemExit("NO_GO: transformation did not change " + name)
    # Validate everything before first mutation.
    for name, value in changed.items():
        (root / s9.BASE / name).write_text(value)
    print("S9 three-file local allocation experiment installed in offline BSP workspace.")
    print("NOT A DS3 FIX: no UHID completion identity, no remote handshake, no security workaround.")
    print("Next: build using build_bsp_arm32_offline.sh and compare ELF artifacts.")

if __name__ == "__main__":
    main()
