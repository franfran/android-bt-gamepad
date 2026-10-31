"""Read-only, byte-pinned M3 Bluetooth.apk HID Host verification.

Supply the owner-original installed M3 APK locally. No APK bytes, MAC addresses
or proprietary assets belong in Git. Requires only Python 3 standard library.
These static checks do NOT imply an actual DS3 attempt reached Java.
"""
import hashlib
import struct
import sys
import zipfile

SHA256 = "d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f"


def verify(path):
    with open(path, "rb") as f:
        apk = f.read()
    digest = hashlib.sha256(apk).hexdigest()
    if digest != SHA256:
        raise ValueError(f"wrong original M3 Bluetooth.apk SHA256: {digest}")
    with zipfile.ZipFile(path) as z:
        dex = z.read("classes.dex")
    if not dex.startswith(b"dex\n"):
        raise ValueError("classes.dex is not DEX")

    def code(offset):
        regs, ins, outs, tries, debug, count = struct.unpack_from("<HHHHII", dex, offset)
        return list(struct.unpack_from("<" + "H" * count, dex, offset + 16))

    callback = code(0x26F254)  # HidHostService.onConnectStateChanged([B,I)
    if not (callback[2] == 0x3112 and callback[3] == 0x206E
            and callback[4] == 0x124C and callback[13] == 0x206E
            and callback[14] == 0x125C):
        raise AssertionError("unexpected native-event to Handler message-3 path")

    hal = code(0x26EC38)  # HidHostService.convertHalState(I)I
    if (hal[1] & 255) != 0x2B:
        raise AssertionError("HAL conversion packed-switch absent")
    payload = 1 + hal[2] + (hal[3] << 16)
    if (hal[payload:payload+4]) != [0x0100, 4, 0, 0]:
        raise AssertionError("HAL switch keys changed")
    states = {}
    for n in range(4):
        o = payload + 4 + 2*n
        target = 1 + hal[o] + (hal[o+1] << 16)
        if (hal[target] & 255) == 0x12:  # const/4 -> return
            if (hal[target+1] & 255) != 0x0F:
                raise AssertionError("HAL switch return changed")
            states[n] = (hal[target] >> 12) & 15
        elif (hal[target] & 255) == 0x0F:  # initialized v0=0
            states[n] = 0
        else:
            raise AssertionError("HAL switch destination changed")
    if states != {0: 2, 1: 1, 2: 0, 3: 3}:
        raise AssertionError(f"unexpected HAL state conversion: {states}")

    msg = code(0x26DC8C)  # HidHostService$1.handleMessage(Message)
    if (msg[14] & 255) != 0x2B:
        raise AssertionError("handler packed-switch absent")
    payload = 14 + msg[15] + (msg[16] << 16)
    if msg[payload:payload+4] != [0x0100, 16, 1, 0]:
        raise AssertionError("handler switch keys changed")
    pos = payload + 4 + 2*(3 - 1)
    if 14 + msg[pos] + (msg[pos+1] << 16) != 0x0195:
        raise AssertionError("handler case 3 destination changed")
    if msg[452:455] != [0x206E, 0x5FB3, 0x0004]:
        raise AssertionError("okToConnect invoke changed")
    if msg[464:467] != [0x2071, 0x5F92, 0x0054]:
        raise AssertionError("access$600 call changed")

    check = code(0x26E880)  # HidHostService.okToConnect
    if check[35:38] != [0x206E, 0x5517, 0x0080]:
        raise AssertionError("AdapterService.getBondState invoke changed")
    if check[39:42] != [0x0513, 12, 0x5432]:
        raise AssertionError("BOND_BONDED=12 check changed")

    unplug = code(0x26E68C)  # HidHostService.access$600
    if unplug[0:3] != [0x2070, 0x5FC9, 0x0021]:
        raise AssertionError("virtualUnPlugNative delegate changed")

    return {"verified_sha256": digest,
            "native_hal_states": states,
            "java_bond_gate": "BOND_BONDED",
            "rejection": "virtualUnPlugNative",
            "actual_DS3_runtime_branch": "NOT_PROVEN"}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 verify_m3_hid_gate.py /private/M3-Bluetooth.apk")
    print(verify(sys.argv[1]))
