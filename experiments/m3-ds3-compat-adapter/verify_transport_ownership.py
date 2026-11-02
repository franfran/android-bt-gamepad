#!/usr/bin/env python3
"""Pinned, read-only H618 source gate for PR #52 I1/I2. Never connects to Bluetooth.

Fetches allowlisted Git blobs from immutable public commit or reads a local
system/bt source tree. Verifies Git SHA-1 blobs before asserting source facts.
A PASS proves source shape only, NOT a supported plugin or working adapter.
"""
import argparse
import hashlib
import pathlib
import re
import sys
import urllib.error
import urllib.request

COMMIT = "250eabfc529518b7f26432663ed0a867ab2f625d"
BASE = "https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/" + COMMIT + "/system/bt/"
# Immutable git blob IDs from system/bt tree d6f07310f73694977b301eac63d67b219ca20625.
BLOBS = {
    "btif/src/bluetooth.cc": "a72f787f5425cca1c82f007408f2f545ca77c9be",
    "btif/src/stack_manager.cc": "ab247345dfc38263c3df55e83a24626ed16164e9",
    "btcore/src/module.cc": "aba22342201e8d9145bc02624b53dacad4d02bb8",
    "stack/hid/hidh_conn.cc": "87ded1c07670aec120017f54f17bccc59fe2cdb9",
    "bta/jv/bta_jv_act.cc": "13fa89953495e100bd81984a0149905a68dc98a7",
    "stack/l2cap/l2c_api.cc": "c8f2659efc93f1b6f86576986be4ea0b8eec561e",
    "stack/gap/gap_conn.cc": "0f0026f712288860854231c6527465d89ef0b3b8",
    "btif/src/btif_sock_l2cap.cc": "a5a9857dbd97b465df763ad86540001873275fad",
    "gd/hal/hci_hal_android_hidl.cc": "4979ef056436e797f16ee899df9566297a130f50",
}

# These expressions are evidence-contract assertions, not general C++ parsers.
# Missing/moved checks MUST fail closed and trigger human review.
CHECKS = {
    "HID host selected internally": (
        "btif/src/bluetooth.cc",
        r"if\s*\(is_profile\(profile_id,\s*BT_PROFILE_HIDHOST_ID\)\)\s*return btif_hh_get_interface\(\)",
    ),
    "built-in stack module table": (
        "btif/src/stack_manager.cc",
        r"#ifdef STATIC_LIBBLUETOOTH[\s\S]*?module_table\[\][\s\S]*?#else[\s\S]*?get_module\(name\)",
    ),
    "module symbol lookup is not a loader": (
        "btcore/src/module.cc",
        r"dlsym\(RTLD_DEFAULT,\s*name\)",
    ),
    "HID control plus interrupt registered": (
        "stack/hid/hidh_conn.cc",
        r"L2CA_Register2\(HID_PSM_CONTROL,[\s\S]*?BTA_SEC_AUTHENTICATE\s*\|\s*BTA_SEC_ENCRYPT[\s\S]*?L2CA_Register2\(HID_PSM_INTERRUPT,[\s\S]*?BTA_SEC_AUTHENTICATE\s*\|\s*BTA_SEC_ENCRYPT",
    ),
    "Classic HID special PSM checks": (
        "bta/jv/bta_jv_act.cc",
        r"case BT_PSM_HIDC:\s*case BT_PSM_HIDI:[\s\S]*?!bta_sys_is_register\(BTA_ID_HD\)\s*\|\|\s*!bta_sys_is_register\(BTA_ID_HH\)",
    ),
    "JV Classic socket gate": (
        "bta/jv/bta_jv_act.cc",
        r"bta_jv_l2cap_connect\([\s\S]*?bta_jv_check_psm\(remote_psm\)",
    ),
    "fixed PSM can replace callback registry": (
        "stack/l2cap/l2c_api.cc",
        r"if\s*\(\(psm\s*>=\s*0x1001\)\s*&&\s*\(p_cb_info\.pL2CA_ConnectInd_Cb\s*==\s*NULL\)\)[\s\S]*?l2cu_find_rcb_by_psm\(vpsm\)[\s\S]*?p_rcb->api\s*=\s*p_cb_info",
    ),
    "Classic GAP registers sockets via L2CAP": (
        "stack/gap/gap_conn.cc",
        r"if\s*\(transport\s*==\s*BT_TRANSPORT_BR_EDR\)[\s\S]*?L2CA_Register2\(psm,\s*conn\.reg_info",
    ),
    "managed Classic sockets use JV": (
        "btif/src/btif_sock_l2cap.cc",
        r"BTA_JvL2capStartServer\([\s\S]*?BTA_JvL2capConnect\(",
    ),
    "HCI transport HAL initializes callback owner": (
        "gd/hal/hci_hal_android_hidl.cc",
        r"IBluetoothHci::getService\(\)[\s\S]*?initialize(?:_1_1)?\(callbacks_\)",
    ),
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_file(path: str, root: pathlib.Path | None) -> bytes:
    if root is not None:
        return (root / path).read_bytes()
    with urllib.request.urlopen(BASE + path, timeout=20) as response:
        data = response.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError("source file oversized: " + path)
    return data


def check_contract(texts: dict[str, str]) -> list[str]:
    errors = []
    for name, (path, expression) in CHECKS.items():
        if re.search(expression, texts[path], flags=re.MULTILINE) is None:
            errors.append(name + ": source changed or evidence missing in " + path)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=pathlib.Path,
                        help="local system/bt source tree (not a full Android BSP)")
    args = parser.parse_args()
    texts = {}
    for path, expected in BLOBS.items():
        try:
            data = load_file(path, args.source_root)
        except (OSError, urllib.error.URLError, ValueError) as error:
            print("NO_GO: unable to read pinned source", path, str(error), file=sys.stderr)
            return 2
        sha = git_blob_sha(data)
        if sha != expected:
            print("NO_GO: Git blob mismatch", path, "expected", expected, "actual", sha,
                  file=sys.stderr)
            return 2
        texts[path] = data.decode("utf-8")
    errors = check_contract(texts)
    for failure in errors:
        print("NO_GO:", failure, file=sys.stderr)
    if errors:
        return 1
    print(f"PASS: {len(BLOBS)} pinned Git blobs, {len(CHECKS)} source assertions")
    print("DECISION: fixed Classic HID PSMs are NOT proven safe for a second owner")
    print("LIMIT: no Bluetooth I/O, no OEM ABI validation, no plugin/runtime claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
