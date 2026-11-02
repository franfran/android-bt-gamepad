#!/usr/bin/env python3
"""Check pinned H618 metadata-only auth trace and run synthetic classifier tests.

Only reads source/fixture files. --source-tree performs git apply --check at
the exact pinned HEAD without applying or building any Android artifacts.
"""
import argparse
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
PATCH = HERE / "h618_legacy_auth_decision_trace_disabled.patch"
PIN = "250eabfc529518b7f26432663ed0a867ab2f625d"
MACRO = "RETROBOX_DS3_LEGACY_AUTH_TRACE"
EXPECTED = {
    "system/bt/stack/btm/btm_sec.cc",
    "system/bt/btif/src/btif_dm.cc",
}


def check_patch():
    content = PATCH.read_text()
    paths = set()
    observer_lines = []
    for part in content.split("diff --git ")[1:]:
        name = part.splitlines()[0].split()
        left, right = name[0].removeprefix("a/"), name[1].removeprefix("b/")
        assert left == right
        paths.add(left)
        assert "new file mode" not in part
        assert not any(row.startswith("-") and not row.startswith("---")
                       for row in part.splitlines())
        for block in part.split("@@ -")[1:]:
            lines = [row[1:] for row in block.splitlines()
                     if row.startswith("+") and not row.startswith("+++")]
            assert lines and lines[0] == f"#if defined({MACRO})"
            assert lines[-1] == "#endif"
            observer_lines.extend(lines)
    assert paths == EXPECTED, paths
    new_source = "\n".join(observer_lines)
    assert "BTM_TRACE_EVENT" in new_source
    assert "BTIF_TRACE_EVENT" in new_source
    assert "ui_pin_reply" in new_source
    assert "key_request" in new_source
    assert "key_notification" in new_source
    assert "hci_completion" in new_source
    # No identifier or cryptographic material may be in the new logs.
    for secret in ("ToString(", "bd_addr.ToString", "p_bda.ToString",
                   "pin_code.pin", "link_key,", "p_dev_rec->link_key",
                   "btsnd_hcic_pin_code", "btsnd_hcic_auth_request"):
        assert secret not in new_source, secret
    assert "BTM_SUCCESS_NO_SECURITY" not in new_source
    print("PASS: source additions are guarded, metadata-only, and read-only")


def check_source(tree):
    head = subprocess.check_output(
        ["git", "-C", str(tree), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != PIN:
        raise SystemExit(f"NO_GO: full BSP HEAD {head} is not {PIN}")
    subprocess.run(["git", "-C", str(tree), "apply", "--check",
                    str(PATCH)], check=True)
    print("PASS: git apply --check against exact pinned H618 checkout")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-tree", type=Path)
    opts = parser.parse_args()
    check_patch()
    subprocess.run(["python3", str(HERE / "test_analyze_legacy_auth_trace.py")],
                   check=True)
    if opts.source_tree:
        check_source(opts.source_tree)
    else:
        print("NOT CHECKED: full pinned BSP apply and Android/ARM32 build")
