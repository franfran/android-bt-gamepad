#!/usr/bin/env python3
"""Read-only Android 12 BSP build preflight. No device or build operations."""
import argparse
import pathlib
import subprocess
import sys

EXPECTED = "250eabfc529518b7f26432663ed0a867ab2f625d"
REQUIRED = (
    "build/envsetup.sh",
    "build/soong/soong_ui.bash",
    "system/bt/main/Android.bp",
    "system/bt/btif/Android.bp",
    "system/bt/btif/co/bta_hh_co.cc",
    "system/bt/btif/src/btif_hh.cc",
    "system/bt/btif/include/btif_hh.h",
    "prebuilts/clang/host",
    "device/softwinner/apollo/AndroidProducts.mk",
    "device/softwinner/apollo/apollo_p1.mk",
)

def git_value(path, *args):
    proc = subprocess.run(["git", "-C", str(path), *args],
                          capture_output=True, text=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None

def run(root):
    failures = []
    for part in REQUIRED:
        if not (root / part).exists():
            failures.append("missing: " + part)

    # BPI publishes a monolithic Git checkout (without .repo). A separate
    # repo-managed checkout is also accepted if the actual BT project is pinned.
    bt = root / "system/bt"
    bt_head = git_value(bt, "rev-parse", "HEAD") if bt.is_dir() else None
    root_head = git_value(root, "rev-parse", "HEAD")
    root_top = git_value(root, "rev-parse", "--show-toplevel")
    bt_top = git_value(bt, "rev-parse", "--show-toplevel") if bt.is_dir() else None
    if bt_head != EXPECTED:
        failures.append("system/bt revision mismatch/unverified: expected " +
                        EXPECTED + ", got " + str(bt_head))
    if not (root / ".repo").exists():
        # Ensure that the BT files are in the pinned monorepo, not a stray
        # nested checkout or an accidentally unpinned checkout.
        if not root_top or not bt_top or pathlib.Path(root_top).resolve() != root or bt_top != root_top or root_head != EXPECTED:
            failures.append("neither a .repo checkout nor the pinned BPI monorepo root")
        else:
            print("Source layout: pinned BPI monorepo (no .repo required)")
    else:
        print("Source layout: Android repo-managed workspace")

    print("Build preflight:", root)
    if failures:
        for issue in failures:
            print("NO_GO:", issue)
        print("No build executed.")
        return 1
    print("PASS: basic BSP layout and pinned source revision")
    print("NOT VERIFIED: oversized upstream files, lunch/32-bit variant, dependency closure, Soong compilation or OEM ABI")
    print("Next: inspect BPI README missing-file requirements, verify lunch, then build offline.")
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=pathlib.Path)
    args = parser.parse_args()
    sys.exit(run(args.root.resolve()))
