#!/usr/bin/env python3
"""Check disabled request-ref overlay and exercise host-only ref pool.

--source-tree optionally tests sequential git apply on COPY of exact pinned
public H618 files; original tree is never modified or configured.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ACL = HERE / "h618_acl_epoch_observe_disabled.patch"
REQ = HERE / "h618_request_bound_btm_callback_disabled.patch"
HEADER = HERE / "request_refs.h"
TEST = HERE / "test_request_refs.cc"
PIN = "250eabfc529518b7f26432663ed0a867ab2f625d"


def validate_content():
    patch = REQ.read_text()
    parts = patch.split("diff --git ")[1:]
    expected = {
        "system/bt/stack/l2cap/l2c_link.cc",
        "system/bt/stack/l2cap/l2c_csm.cc",
        "system/bt/stack/l2cap/l2c_utils.cc",
        "system/bt/stack/l2cap/retrobox_request_refs.h",
    }
    actual = set()
    for part in parts:
        first = part.splitlines()[0].split()
        left = first[0].removeprefix("a/")
        right = first[1].removeprefix("b/")
        assert left == right, first
        actual.add(left)
        if "new file mode" in part:
            new_lines = [
                line[1:] for line in part.splitlines()
                if line.startswith("+") and not line.startswith("+++")
            ]
            assert "\n".join(new_lines) + "\n" == HEADER.read_text()
    assert actual == expected, actual
    # Only callback correlation changes. BTM flags, auth, bonding, HCI intact.
    assert "system/bt/stack/btm/btm_sec.cc" not in patch
    assert "BTA_SEC_AUTHENTICATE" not in patch
    assert "BOND_BONDED" not in patch
    assert "btsnd_hcic_auth_request" not in patch
    assert "RETROBOX_DS3_REQUEST_REF_OBSERVE" in patch
    assert "RETROBOX_DS3_ACL_EPOCH_OBSERVE" in patch
    assert "retrobox_begin_btm_request_ref" in patch
    assert "retrobox_retire_refs_for_ccb" in patch
    assert "retrobox_retire_refs_for_lcb" in patch
    assert "&l2c_link_sec_comp, p_ccb" in patch  # fallback unchanged
    assert "l2c_link_sec_comp2(*bda, transport, match, status);" in patch
    print("PASS: source overlay limited to request-token transport and guarded")


def run_host_test(sanitize):
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "request_ref_test"
        cmd = [
            "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic",
        ]
        if sanitize:
            cmd += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
        cmd += ["-I", str(HERE), str(TEST), "-o", str(exe)]
        subprocess.run(cmd, check=True)
        subprocess.run([str(exe)], check=True)


def verify_exact_checkout(tree):
    sha = subprocess.check_output(
        ["git", "-C", str(tree), "rev-parse", "HEAD"], text=True,
    ).strip()
    if sha != PIN:
        raise SystemExit(f"NO_GO: BSP HEAD {sha} does not match pin {PIN}")

    files = [
        "system/bt/stack/l2cap/l2c_link.cc",
        "system/bt/stack/l2cap/l2c_csm.cc",
        "system/bt/stack/l2cap/l2c_utils.cc",
    ]
    with tempfile.TemporaryDirectory() as temp:
        scratch = Path(temp)
        for name in files:
            output = scratch / name
            output.parent.mkdir(parents=True, exist_ok=True)
            content = subprocess.check_output(
                ["git", "-C", str(tree), "show", f"{PIN}:{name}"]
            )
            output.write_bytes(content)
        # No git repo or index needed for ordinary local git apply.
        subprocess.run(["git", "-C", str(scratch), "apply", "--check",
                        str(ACL)], check=True)
        subprocess.run(["git", "-C", str(scratch), "apply", str(ACL)],
                       check=True)
        subprocess.run(["git", "-C", str(scratch), "apply", "--check",
                        str(REQ)], check=True)
        print("PASS: sequential ACL then request-ref patch applies in scratch")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-tree", type=Path)
    opts = parser.parse_args()
    validate_content()
    run_host_test(False)
    run_host_test(True)
    if opts.source_tree:
        verify_exact_checkout(opts.source_tree)
    else:
        print("NOT CHECKED: full-tree sequential git apply and Android build")
