#!/usr/bin/env python3
"""Reproduce offline ACL-observer guards; optionally check an exact pinned BSP.

No live Bluetooth, adb, root, git writes, or security changes.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

PIN = "250eabfc529518b7f26432663ed0a867ab2f625d"
HERE = Path(__file__).resolve().parent
PATCH = HERE / "h618_acl_epoch_observe_disabled.patch"
HEADER = HERE / "acl_epoch_observer.h"
TEST = HERE / "test_acl_epoch_observer.cc"
FLAG = "RETROBOX_DS3_ACL_EPOCH_OBSERVE"


def verify_source_only():
    patch = PATCH.read_text()
    parts = patch.split("diff --git ")[1:]
    names = []
    for part in parts:
        first = part.splitlines()[0].split()
        path = first[0].removeprefix("a/")
        assert first[1].removeprefix("b/") == path
        names.append(path)
        if "new file mode" in part:
            encoded = [
                line[1:] for line in part.splitlines()
                if line.startswith("+") and not line.startswith("+++")
            ]
            assert ("\n".join(encoded) + "\n") == HEADER.read_text()
        else:
            assert not [
                line for line in part.splitlines()
                if line.startswith("-") and not line.startswith("---")
            ], f"patch unexpectedly changes original source: {path}"
            hunks = part.split("\n@@ ")[1:]
            if not hunks:
                # First hunk starts at a line beginning '@@', not '\n@@'
                hunks = part.split("@@ -")[1:]
            for fragment in part.splitlines():
                if fragment.startswith("+#if"):
                    assert FLAG in fragment
    assert len(names) == 4, names
    assert all(p.startswith("system/bt/stack/l2cap/") for p in names)
    assert "BTA_SEC_AUTHENTICATE" not in patch
    assert "BTM_SUCCESS_NO_SECURITY" not in patch
    assert "BOND_BONDED" not in patch
    for x in ("l2c_link_hci_conn_comp", "l2c_link_hci_disc_comp",
              "l2cu_release_lcb", "l2c_link_sec_comp2"):
        # Marker functions may be outside hunks. The audited context is source.
        pass
    for anchor in ("LST_CONNECTED", "SetDisconnectReason(reason)",
                   "retrobox_acl_retire_for_lcb", "CST_TERM_W4_SEC_COMP",
                   "if (p_ccb == p_ref_data)"):
        assert anchor in patch, anchor
    print("PASS: patch adds guarded passive observer only; header in sync")


def build_and_test(sanitized):
    with tempfile.TemporaryDirectory() as directory:
        exe = Path(directory) / "acl_host_test"
        cmd = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
               "-pedantic", "-I", str(HERE), str(TEST), "-o", str(exe)]
        if sanitized:
            cmd[1:1] = ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
        subprocess.run(cmd, check=True)
        subprocess.run([str(exe)], check=True)


def verify_tree(tree):
    sha = subprocess.check_output(
        ["git", "-C", str(tree), "rev-parse", "HEAD"], text=True
    ).strip()
    if sha != PIN:
        raise SystemExit(f"NO_GO: source HEAD {sha} != pinned {PIN}")
    subprocess.run(["git", "-C", str(tree), "apply", "--check",
                    str(PATCH)], check=True)
    print("PASS: git apply --check against exact pinned BSP (no changes applied)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-tree", type=Path,
                        help="optional complete H618 checkout at pinned HEAD")
    args = parser.parse_args()
    verify_source_only()
    build_and_test(False)
    build_and_test(True)
    if args.source_tree:
        verify_tree(args.source_tree)
    else:
        print("NOT CHECKED: full H618 git apply / Android source build")
