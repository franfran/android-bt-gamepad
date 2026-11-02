# I1 preliminary: HID Host interface is not an external plugin API

Status: **PARTIAL / source reconnaissance only**, not a completed pinned BSP inventory.

## Finding
In multiple AOSP Fluoride source revisions, `btif/src/bluetooth.cc` has an internal `get_profile_interface(profile_id)` selector, whose `BT_PROFILE_HIDHOST_ID` case returns `btif_hh_get_interface()`. This is a **compile-time-wired built-in profile interface**, not evidence of an arbitrary third-party plugin registrar or externally loadable HID Host module.

Examples:
- [AOSP static dispatch, source commit bd1cf780a1684dd9b2c859a3f0a433a69a377175](https://android.googlesource.com/platform/system/bt/+/bd1cf780a1684dd9b2c859a3f0a433a69a377175/btif/src/bluetooth.cc)
- [AOSP preexisting source, same static HID Host interface pattern](https://android.googlesource.com/platform/system/bt/+/oreo-m3-release/btif/src/bluetooth.cc)

**Important limitation:** These AOSP revisions are illustrative, NOT proof of identical implementation in the [pinned H618 BSP](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/tree/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt). We have NOT yet finished searching that pinned tree for OEM-specific hook points. Also, dynamic linking inside the Bluetooth stack does not imply a supported HID plugin ABI.

## Consequences
- A conventional APK cannot replace the built-in `btif_hh_get_interface()` simply by adding an .so.
- Do not use unreviewed `dlopen`, process injection or symbol interposition as a substitute for a documented extension interface.
- Next source-only tasks: inspect pinned BSP `btif/src/bluetooth.cc`, `btif/src/btif_hh.cc`, `main/Android.bp`, `service`/JNI integration and OEM/vendor extension paths; enumerate any real supported registration seam and ABI. Explicitly record searched files and negative evidence.
- If no extension surface is found, assess minimal source adapter (candidate C) against independent daemon ownership (B), rather than inventing a plugin interface.

No target device actions, compilation, security changes or deployment.
