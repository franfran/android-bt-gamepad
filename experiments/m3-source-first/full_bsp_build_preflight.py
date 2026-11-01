#!/usr/bin/env python3
"""Offline read-only preflight for a FULL pinned Android BSP Soong build.

Usage: python3 experiments/m3-source-first/full_bsp_build_preflight.py /path/to/android-root
Never runs lunch, compiles, flashes, replaces libraries or touches a device.
"""
import argparse
import pathlib
import subprocess
import sys

EXPECTED="250eabfc529518b7f26432663ed0a867ab2f625d"
REQUIRED=(
    "build/envsetup.sh",
    "build/soong/soong_ui.bash",
    "system/bt/main/Android.bp",
    "system/bt/btif/Android.bp",
    "system/bt/btif/co/bta_hh_co.cc",
    "system/bt/btif/src/btif_hh.cc",
    "system/bt/btif/include/btif_hh.h",
    "prebuilts/clang",
)
def run(root):
    failures=[]
    for part in REQUIRED:
        if not (root/part).exists():
            failures.append("missing: "+part)
    bt=root/"system/bt"
    if (bt/".git").exists() or (root/".repo").exists():
        cmd=["git","-C",str(bt),"rev-parse","HEAD"]
        p=subprocess.run(cmd,capture_output=True,text=True)
        if p.returncode or p.stdout.strip()!=EXPECTED:
            failures.append("system/bt SHA mismatch/unverified; expected "+EXPECTED+" got "+p.stdout.strip())
    else:
        failures.append("cannot verify pinned system/bt git revision")
    if not (root/".repo").exists():
        failures.append("not a repo-managed full Android checkout (.repo missing)")
    print("Build preflight:",root)
    if failures:
        for reason in failures: print("NO_GO:",reason)
        print("No build executed.")
        return 1
    print("PASS: basic full-tree layout and pinned system/bt Git commit")
    print("NOT proof of product target, Soong dependency closure, OEM ABI or successful build.")
    print("Next: independently select a verified lunch target and execute a controlled Soong build.")
    return 0
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=pathlib.Path)
    args=ap.parse_args()
    sys.exit(run(args.root.resolve()))
