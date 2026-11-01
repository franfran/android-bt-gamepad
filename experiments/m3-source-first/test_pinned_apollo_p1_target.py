#!/usr/bin/env python3
"""Validate a candidate Apollo P1 lunch target in an immutable public BSP.

No Android build and no assertion that this target matches the M3 OEM binary.
"""
import urllib.request
REV="250eabfc529518b7f26432663ed0a867ab2f625d"
BASE=f"https://raw.githubusercontent.com/BPI-SINOVOIP/BPI-H618-Android12/{REV}/device/softwinner/apollo/"
def get(name):
    with urllib.request.urlopen(BASE+name,timeout=30) as response:
        return response.read().decode()
def main():
    products=get("AndroidProducts.mk")
    definition=get("apollo_p1.mk")
    config=get("BoardConfig.mk")
    assert "$(LOCAL_DIR)/apollo_p1.mk" in products
    assert "apollo_p1-userdebug" in products
    assert "PRODUCT_NAME := apollo_p1" in definition
    assert "PRODUCT_DEVICE := apollo-p1" in definition
    assert "TARGET_BOARD_PLATFORM := apollo" in config
    assert "TARGET_BOARD_KERN_VER := 5.4" in config
    print("PASS pinned BSP has candidate lunch target: apollo_p1-userdebug")
    print("NOT verified: M3 OEM product equivalence, libbluetooth 32-bit variant, device ABI, vendor JNI")
if __name__=="__main__": main()
