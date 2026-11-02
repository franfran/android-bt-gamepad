#!/usr/bin/env python3
"""Verify default-off UHID deny fence; optional exact H618 BSP patch check.

No ADB, Bluetooth operations, firmware edits, or source-tree modifications.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
PATCH = HERE / "h618_uhid_candidate_fence_disabled.patch"
HEADER = HERE / "candidate_uhid_fence.h"
TEST = HERE / "test_candidate_uhid_fence.cc"
PIN = "250eabfc529518b7f26432663ed0a867ab2f625d"
FLAG = "RETROBOX_DS3_UHID_FENCE_RESEARCH"


def source_guards():
    data = PATCH.read_text()
    assert data.count("diff --git ") == 2
    assert "system/bt/btif/co/bta_hh_co.cc" in data
    assert "system/bt/btif/co/retrobox_candidate_uhid_fence.h" in data
    assert data.count(f"#if defined({FLAG})") >= 3
    assert "UHID_CREATE || ev->type == UHID_INPUT" in data
    assert "return -EACCES;" in data
    assert "return g_retrobox_candidate_fence.RegisterCandidate(ticket);" in data
    assert "return g_retrobox_candidate_fence.Revoke(ticket);" in data
    assert "AllowKernelEvent(p_dev->fd, true)" in data
    assert "BOND_BONDED" not in data
    assert "BTM_SUCCESS_NO_SECURITY" not in data
    assert "BTA_SEC_AUTHENTICATE" not in data
    assert "HCI_AUTH" not in data
    section = data.split(
        "diff --git a/system/bt/btif/co/retrobox_candidate_uhid_fence.h", 1
    )[1]
    added = [
        row[1:] for row in section.splitlines()
        if row.startswith("+") and not row.startswith("+++")
    ]
    assert "\n".join(added) + "\n" == HEADER.read_text()
    print("PASS: pointer-only candidate registration has no security grant")


def run_host_test(sanitized):
    with tempfile.TemporaryDirectory() as folder:
        binary = Path(folder) / "uhid_fence_host"
        command = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                   "-pedantic", "-pthread"]
        if sanitized:
            command += ["-fsanitize=address,undefined",
                        "-fno-omit-frame-pointer"]
        command += [str(TEST), "-o", str(binary)]
        subprocess.run(command, check=True)
        subprocess.run([str(binary)], check=True)


def source_check(tree):
    revision = subprocess.check_output(
        ["git", "-C", str(tree), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != PIN:
        raise SystemExit(f"NO_GO: BSP HEAD {revision} != pinned {PIN}")
    subprocess.run(["git", "-C", str(tree), "apply", "--check", str(PATCH)],
                   check=True)
    print("PASS: git apply --check for exact H618 checkout (not applied)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-tree", type=Path,
                        help="optional exact H618 checkout at pinned SHA")
    args = parser.parse_args()
    source_guards()
    run_host_test(False)
    run_host_test(True)
    if args.source_tree:
        source_check(args.source_tree)
    else:
        print("NOT RUN: complete H618 git apply --check and Soong target build")
