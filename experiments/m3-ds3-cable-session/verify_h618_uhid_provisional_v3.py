#!/usr/bin/env python3
"""Offline source guard and host test for provisional-before-classification.

Optional pinned full BSP git apply --check; never applies any files to source.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
PATCH = HERE / "h618_uhid_provisional_v3_disabled.patch"
HEADER = HERE / "provisional_uhid_gate.h"
TEST = HERE / "test_provisional_uhid_gate.cc"
PIN = "250eabfc529518b7f26432663ed0a867ab2f625d"
FLAG = "RETROBOX_DS3_UHID_PROVISIONAL_V3_RESEARCH"


def guard_check():
    patch = PATCH.read_text()
    assert patch.count("diff --git ") == 2
    assert patch.count(f"#if defined({FLAG})") >= 4
    assert patch.count("g_provisional_uhid.Open(p_dev->fd, dev_handle)") == 2
    assert "g_provisional_uhid.WithWrite(fd, kind" in patch
    assert "btif_hh_cb.device_num--;" in patch
    assert "p_dev->dev_handle = BTA_HH_INVALID_HANDLE;" in patch
    assert "BTA_SEC_AUTHENTICATE" not in patch
    assert "BOND_BONDED" not in patch
    assert "BTM_SUCCESS_NO_SECURITY" not in patch
    original_section, header_section = patch.split(
        "diff --git a/system/bt/btif/co/retrobox_provisional_uhid_gate.h", 1
    )
    assert not any(
        line.startswith("-") and not line.startswith("---")
        for line in original_section.splitlines()
        if line.startswith("-") and "return 0;" not in line
        and not line.startswith("-}")
        and "Internal function to parse" not in line
        and line != "-"
    ), "unexpected non-wrapper source removal"
    added = [
        line[1:] for line in header_section.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    assert "\n".join(added) + "\n" == HEADER.read_text()
    # The two branch-local provisional gates appear BEFORE the poll flag.
    for hunk in original_section.split("@@ -"):
        if "g_provisional_uhid.Open(p_dev->fd, dev_handle)" in hunk:
            assert hunk.index("g_provisional_uhid.Open") < hunk.index(
                "p_dev->hh_keep_polling = 1;"
            )
    print("PASS: default-off provisional-before-poll UHID source guards")


def compile_test(sanitized):
    with tempfile.TemporaryDirectory() as work:
        output = Path(work) / "provisional_host"
        cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
               "-pedantic", "-pthread"]
        if sanitized:
            cmd.extend(["-fsanitize=address,undefined",
                        "-fno-omit-frame-pointer"])
        cmd.extend(["-I", str(HERE), str(TEST), "-o", str(output)])
        subprocess.run(cmd, check=True)
        subprocess.run([str(output)], check=True)


def check_bsp(source_tree):
    commit = subprocess.check_output(
        ["git", "-C", str(source_tree), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if commit != PIN:
        raise SystemExit(f"NO_GO: BSP revision {commit} differs from {PIN}")
    subprocess.run(
        ["git", "-C", str(source_tree), "apply", "--check", str(PATCH)],
        check=True,
    )
    print("PASS: exact pinned full-tree patch apply check (no writes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-tree", type=Path,
                        help="optional exact pinned full H618 checkout")
    args = parser.parse_args()
    guard_check()
    compile_test(False)
    compile_test(True)
    if args.source_tree:
        check_bsp(args.source_tree)
    else:
        print("NOT CHECKED: full BSP git apply and Android target build")
