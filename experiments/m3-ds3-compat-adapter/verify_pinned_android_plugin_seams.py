#!/usr/bin/env python3
"""Offline-target, immutable-source audit of Android 12 Bluetooth plugin seams.

Host-only: fetches 10 public allowlisted upstream Git blobs, checks exact
Git blob SHA-1, then verifies narrowly scoped source predicates. No device
I/O, no proprietary data, no Android build, no runtime plugin/injection.
"""
import hashlib
import json
import re
import urllib.request

PIN = "250eabfc529518b7f26432663ed0a867ab2f625d"
ROOT = "https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/" + PIN + "/"
FILES = {
    "packages/apps/Bluetooth/jni/com_android_bluetooth_btservice_AdapterService.cpp": "62c7d522d45202947d4d23e2f518e1f626ecfc02",
    "packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp": "074e39d5b024c921ca0c4ff3451cad732b40ded3",
    "packages/apps/Bluetooth/src/com/android/bluetooth/btservice/AdapterService.java": "0f8d8691f777af3895c78612a8ea19e331429d88",
    "packages/apps/Bluetooth/src/com/android/bluetooth/btservice/Config.java": "41535377a0db74f0237efc513112f613f25a1f51",
    "packages/apps/Bluetooth/src/com/android/bluetooth/btservice/ProfileService.java": "f582ae54ad65ca0f6edd7c031ef3e0e2cbcc1de6",
    "packages/apps/Bluetooth/src/com/android/bluetooth/btservice/BondStateMachine.java": "bd2ddd03f56e178f143afc39c1a8058adf626fea",
    "packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java": "f1e974631c85bd86751d456221944a2a68f9567d",
    "packages/apps/Bluetooth/AndroidManifest.xml": "1a92268e7bc728c572da83237fb6de12e2f8d5a0",
    "system/bt/btif/src/btif_hh.cc": "9e5db0c1af234881048732d8bc4816f23b2a33ba",
    "system/bt/stack/hid/hidh_conn.cc": "87ded1c07670aec120017f54f17bccc59fe2cdb9",
}
B = "packages/apps/Bluetooth/"
S = "system/bt/"
# All predicates are source-presence/flow checks, NEVER an exhaustive
# negative conclusion about an unknown OEM extension.
CHECKS = {
    "whole_stack_dlopen_fixed_name": (B + "jni/com_android_bluetooth_btservice_AdapterService.cpp", [
        'dlopen("libbluetooth.so", RTLD_NOW)', "dlsym(handle, sym)"
    ]),
    "profile_selection_closed_known_class_table": (B + "src/com/android/bluetooth/btservice/Config.java", [
        "PROFILE_SERVICES_AND_FLAGS", "HidHostService.class",
        "for (ProfileConfig config : PROFILE_SERVICES_AND_FLAGS)",
        "profiles.add(config.mClass)"
    ]),
    "profile_service_lifecycle_internal": (B + "src/com/android/bluetooth/btservice/ProfileService.java", [
        "mAdapterService.isStartedProfile(mName)", "mAdapterService.addProfile(this)"
    ]),
    "jni_hidhost_single_owner_cleanup_and_init": (B + "jni/com_android_bluetooth_hid_host.cpp", [
        "sBluetoothHidInterface->cleanup()",
        "get_profile_interface(BT_PROFILE_HIDHOST_ID)",
        "sBluetoothHidInterface->init(&sBluetoothHidCallbacks)"
    ]),
    "native_hidhost_callback_single_pointer": (S + "btif/src/btif_hh.cc", [
        "static bthh_callbacks_t* bt_hh_callbacks = NULL",
        "bt_hh_callbacks = callbacks"
    ]),
    "android_hid_binder_privileged_connect": (B + "src/com/android/bluetooth/hid/HidHostService.java", [
        "enforceBluetoothPrivilegedPermission(service)",
        "return service.connect(device)"
    ]),
    "hid_service_export_is_not_permission": (B + "AndroidManifest.xml", [
        'android:name=".hid.HidHostService"', 'android:exported="true"'
    ]),
    "pairing_broadcast_internal_source": (B + "src/com/android/bluetooth/btservice/BondStateMachine.java", [
        "new Intent(BluetoothDevice.ACTION_PAIRING_REQUEST)",
        "mAdapterService.sendOrderedBroadcast(intent, BLUETOOTH_CONNECT"
    ]),
    "app_pin_binder_state_and_permission": (B + "src/com/android/bluetooth/btservice/AdapterService.java", [
        "public boolean setPin(BluetoothDevice device, boolean accept, int len, byte[] pinCode",
        "Utils.checkConnectPermissionForDataDelivery(",
        "!deviceProp.isBondingOrBonded()",
        "service.pinReplyNative("
    ]),
    "existing_hid_psm_native_security": (S + "stack/hid/hidh_conn.cc", [
        "L2CA_Register2(HID_PSM_CONTROL",
        "L2CA_Register2(HID_PSM_INTERRUPT",
        "BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT"
    ]),
}


def git_blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\x00" + data).hexdigest()


def check_texts(texts):
    results = []
    for name, (path, evidence) in CHECKS.items():
        text = texts[path]
        if not all(fragment in text for fragment in evidence):
            raise ValueError("source predicate did not match: " + name)
        results.append(name)
    return results


def fetch_pinned():
    texts = {}
    for path, blob in FILES.items():
        request = urllib.request.Request(ROOT + path, headers={"User-Agent": "retrobox-readonly-plugin-audit"})
        with urllib.request.urlopen(request, timeout=25) as response:
            data = response.read(1100000)
        actual = git_blob_sha(data)
        if actual != blob:
            raise ValueError("pinned Git blob mismatch: " + path)
        texts[path] = data.decode("utf-8")
    return texts


def main():
    try:
        texts = fetch_pinned()
        checks = check_texts(texts)
    except Exception as e:
        print("NO_GO: pinned source audit could not verify: " + type(e).__name__)
        return 2
    print(json.dumps({
        "result": "PUBLIC_SOURCE_SEAMS_VERIFIED_NOT_OEM_PLUGIN_GO",
        "pinned_source": PIN,
        "git_blobs_verified": len(texts),
        "source_predicates_verified": checks,
        "scope": "public H618 Android 12, not OEM M3 proprietary ABI",
        "conclusion": "Narrow app pairing receiver possible in principle; no proven external HID/BTM/Java/UHID plugin ABI",
        "limitations": [
            "Source symbol presence is not a real OEM loader callsite audit",
            "No manifest receiver deliverability, runtime permissions or DS3 PIN suitability tested",
            "No M3 device, live Bluetooth, proprietary binary, root injection or library replacement",
        ]
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
