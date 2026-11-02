#!/usr/bin/env python3
"""Host-only v2 UHID lifecycle patch guard; no device or Android build.

Optionally checks patch application against an exact pinned H618 checkout,
without modifying the source checkout.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
PATCH = HERE / "h618_uhid_lifecycle_v2_disabled.patch"
HEADER = HERE / "candidate_lifecycle_gate.h"
TEST = HERE / "test_candidate_lifecycle_gate.cc"
PIN = "250eabfc529518b7f26432663ed0a867ab2f625d"
FLAG = "RETROBOX_DS3_UHID_LIFECYCLE_V2_RESEARCH"


def validate_patch():
    patch = PATCH.read_text()
    assert patch.count("diff --git ") == 2
    assert "system/bt/btif/co/bta_hh_co.cc" in patch
    assert "system/bt/btif/co/retrobox_candidate_lifecycle_gate.h" in patch
    assert patch.count(f"#if defined({FLAG})") >= 4
    assert "WithKernelWrite(fd, kind" in patch
    assert "IsBlocked(p_dev->fd)" in patch
    assert "Quarantine(ticket)" in patch
    assert "CloseQuarantined(" in patch
    assert "return close(fd) == 0;" in patch
    assert not any(line.startswith("-") and not line.startswith("---")
                   for line in patch.splitlines())
    assert "BOND_BONDED" not in patch
    assert "BTM_SUCCESS_NO_SECURITY" not in patch
    assert "BTA_SEC_AUTHENTICATE" not in patch
    assert "retrobox_register_candidate_v2" in patch
    header_section = patch.split(
        "diff --git a/system/bt/btif/co/retrobox_candidate_lifecycle_gate.h", 1
    )[1]
    lines = [line[1:] for line in header_section.splitlines()
             if line.startswith("+") and not line.startswith("+++")]
    assert "\n".join(lines) + "\n" == HEADER.read_text()
    print("PASS: default-OFF v2 source patch and header integrity")


def test_host(sanitized):
    with tempfile.TemporaryDirectory() as folder:
        binary = Path(folder) / "lifecycle_test"
        command = [
            "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
            "-pthread",
        ]
        if sanitized:
            command.extend(["-fsanitize=address,undefined",
                            "-fno-omit-frame-pointer"])
        command.extend([str(TEST), "-o", str(binary)])
        subprocess.run(command, check=True)
        subprocess.run([str(binary)], check=True)


def check_bsp(source_tree):
    sha = subprocess.check_output([
        "git", "-C", str(source_tree), "rev-parse", "HEAD"
    ], text=True).strip()
    if sha != PIN:
        raise SystemExit(f"NO_GO: BSP HEAD {sha} does not equal pinned {PIN}")
    subprocess.run([
        "git", "-C", str(source_tree), "apply", "--check", str(PATCH)
    ], check=True)
    print("PASS: exact pinned H618 git apply --check (no modifications)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-tree", type=Path,
                        help="optional exact pinned full H618 checkout")
    args = parser.parse_args()
    validate_patch()
    test_host(False)
    test_host(True)
    if args.source_tree:
        check_bsp(args.source_tree)
    else:
        print("NOT CHECKED: full H618 git apply or Android Soong compilation")
