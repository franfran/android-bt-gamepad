# I1 — Original M3 OEM load surface: evidence ledger and plugin falsification boundary

**2026-11-02; Draft PR #52; existing M3 Bluetooth radio, plugin only.** No USB dongle, second radio, source-library rebuild, live device operations, injection, SELinux changes, or system/APK replacement. This report uses previous **exact-original M3 2024 ELF/APK research** (PR #50) and **immutable pinned public H618 source**. It is not a fresh byte-level analysis of the original proprietary binary.

## Evidence grade and ORIGINAL OEM identities (not public binaries)

| Evidence | Recorded provenance | Grade / limits |
|---|---|---|
| M3 running Bluetooth native library | Owner's original process mapping had **\`/system/lib/libbluetooth.so\`** mapped; [PR #50 mapped-native evidence](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-MAPPED-NATIVE-ELF-AND-2025-DIFF-GATE.md). | **Historical OEM observation**, not a new live check |
| Original 2024 \`libbluetooth.so\` | SHA-256 **\`4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85\`**, ELF32 little-endian ARM EABI5, Build ID **\`0d29a62178e43066e018216c1f1d5b18\`**; [PR #51 original handoff](https://github.com/franfran/android-bt-gamepad/blob/feat/m3-ds3-source-first/docs/M3-DS3-SOURCE-FIRST-HANDOFF.md). | **Previously hash-verified exact OEM ELF**; *no new imports/strings/callsites audited* |
| M3 Bluetooth JNI | \`/system/lib/libbluetooth_jni.so\`, SHA-256 **\`1db644b6e2203431e95d55d420729db054fa7f2f8e0bd2f8cbd35a00abf17dfd\`**; [PR #50 initial ELF inventory](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/research/retrobox-stage3a-binary-audit.md). | **Historical inventory**, no current loader callsite verification |
| M3 Bluetooth APK | Original APK SHA-256 **\`d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f\`**; [PR #50 OEM DEX audit](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-HID-DEX-AND-NATIVE-GATES.md). | **Previously verified OEM DEX** confirms \`HidHostService.okToConnect\` and connected-event handler, not an external plugin API |
| M3 Bluetooth HAL | Existing package/service evidence names \`android.hardware.bluetooth@1.0-service\`; [PR #50 binary inventory](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/research/retrobox-stage3a-binary-audit.md). | **Historical service identification**, specific proprietary HAL implementation and extension contract **not** audited |
| Public reference source | [BPI H618 Android 12 \`250eabfc...\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/tree/250eabfc529518b7f26432663ed0a867ab2f625d). | **PROVEN public source behavior**, not byte-identical OEM loader or ABI |

**Actual private-file retrieval boundary:** This research session discovered indexed Library records for \`m3-original-2024-libbluetooth.so\`, \`M3-Bluetooth.apk.zip\`, \`m3-bluetooth-native.zip\`, and \`m3-2025-bluetooth-framework.zip\`. Raw-byte materialization was **refused by the file store**, with no container-backed copy. Therefore **zero new direct OEM ELF/APK readelf/DEX inspections were carried out**. Never claim this ledger is an OEM binary disassembly or complete negative plugin scan.

## Pinned H618: distinguish four loader-like mechanisms

### 1. \`dlopen("libbluetooth.so")\`: it loads the whole stack

[\`system/bt/btcore/src/hal_util.cc:32–57\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btcore/src/hal_util.cc#L32-L57) implements \`hal_util_load_bt_library\` with a fixed \`BLUETOOTH_LIBRARY_NAME "libbluetooth.so"\`. [\`system/bt/service/hal/bluetooth_interface.cc:263–280\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/service/hal/bluetooth_interface.cc#L263-L280) calls the helper to obtain the stack HAL interface. **A \`dlopen\` reference here is NOT evidence for \`dlopen("libds3_plugin.so")\`.** Overriding that object breaks the requirement to leave the existing OEM \`libbluetooth.so\` alone.

### 2. \`dlsym(RTLD_DEFAULT,...)\`: already-loaded internal modules, not a plugin registrar

[\`system/bt/btcore/src/module.cc:56–60\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btcore/src/module.cc#L56-L60) uses \`dlsym(RTLD_DEFAULT,name)\`. [\`btif/src/stack_manager.cc:144–193\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/stack_manager.cc#L144-L193) initializes the **preselected** module set (and supports a compile-time \`STATIC_LIBBLUETOOTH\` table). This does not establish any runtime filesystem scan, arbitrary external \`.so\` loading, multi-listener HID callback mux, or module registration API available to an independent package.

### 3. Vendor HAL ABI exists, but controller transport != HID Host extension

[\`system/bt/hci/include/bt_vendor_lib.h:378–411\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/hci/include/bt_vendor_lib.h#L378-L411) declares a vendor entry symbol \`BLUETOOTH_VENDOR_LIB_INTERFACE\` implementing firmware, power, UART, low-power and audio interface operations. **This header is not proof this particular Android HIDL build calls \`dlopen("libbt-vendor.so")\`, nor proof an external HID policy module can attach to it.** [\`hci/src/hci_layer_android.cc:158–190\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/hci/src/hci_layer_android.cc#L158-L190) initializes controller HCI service callbacks. No per-DS3 native security/bond extension contract has been demonstrated.

### 4. Android Bluetooth profile service registration is an internal package path

[\`Config.java:73–83\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/btservice/Config.java#L73-L83) has a predeclared \`PROFILE_SERVICES_AND_FLAGS\` table with \`HidHostService.class\`. [\`AdapterService.java:299–375\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/btservice/AdapterService.java#L299-L375) has \`addProfile(ProfileService)\`, but registering built-in Java service instances is **not** a documented external \`PackageManager\`-installable HID Host extension.

Moreover [\`btif/src/bluetooth.cc:416–464\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/bluetooth.cc#L416-L464) statically routes \`BT_PROFILE_HIDHOST_ID\` to \`btif_hh_get_interface()\` and [JNI HID Host source](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/jni/com_android_bluetooth_hid_host.cpp#L181-L236) registers an existing callback table. No external callback fanout is established.

## The one extensible-looking feature to NOT confuse with plugin: interop database

The BT interface exposes \`interop_database_add\` ([\`btif/src/bluetooth.cc:611\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/bluetooth.cc#L611)); [\`device/src/interop.cc:80–94\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/device/src/interop.cc#L80-L94) adds a device-prefix-matching entry for an **existing enum feature**. [\`interop.h:30–119\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/device/include/interop.h#L30-L119) defines cases such as pairing retry, existing keyboard fixed PIN workaround, HID supervision timeout and sniff-mode workarounds. **It does not define arbitrary per-device Classic L2CAP authentication callbacks, alter Java \`BOND_BONDED\` policy, or implement UHID SET_REPORT completion.** It is an internal feature flag interface, not a general plugin SDK. No runtime mutation performed.

## Previously *directly* verified OEM DS3 gates relevant to plugin acceptance

- **HCI:** owner's observed DS3 pairing sequence reached authentication and HCI status **0x22 / LMP Response Timeout**. Real cause not established; it is NOT simply "incorrect PIN" by definition.
- **Java:** exact OEM DEX \`HidHostService.okToConnect\` checks \`BOND_BONDED\` and policy. PR #50 resolved exact **JNI state callback → handler \`what=3\` → \`okToConnect\` → conditional \`virtualUnPlugNative\`** static dispatch ([original DEX audit](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-HID-DEX-AND-NATIVE-GATES.md)). The failed live radio session was not shown to reach that Java path.
- **UHID:** owner's original ELF has a no-op SET_REPORT completion and no corresponding request-ID queue in the traced SET path; correct input/report lifecycle is a later separate blocker ([PR #51 evidence handoff](https://github.com/franfran/android-bt-gamepad/blob/feat/m3-ds3-source-first/docs/M3-DS3-SOURCE-FIRST-HANDOFF.md)).

A viable plugin MUST legitimately get callbacks/authority at these specific gates, preserve normal-device security, and not replace the original library or Bluetooth.apk. A separate APK consuming Android Bluetooth events without authority at these gates **cannot** fix the observed failure.

## New reproducible, safely bounded offline evidence tool

[SHA-pinned ELF loader audit](../experiments/m3-ds3-compat-adapter/audit_oem_plugin_elf_offline.py):
- **Read-only**; requires original 2024 library to match exact SHA-256 and Build ID before attributing any findings to OEM.
- Checks **ELF32 ARM little-endian**; \`readelf\` dynamic NEEDED/SONAME; allowed symbol names for \`dlopen\`, \`dlsym\`, \`android_dlopen_ext\`, vendor interface, selected BTIF; \`strings\` restricted to \`lib*.so\` basenames only. No raw string dump, code disassembly or private paths in stdout. It **never** loads the ELF.
- Does **not** infer a loader callsite from an imported symbol or a \`.so\` string. Always returns \`plugin_decision: UNRESOLVED\` until manual OEM control-flow and callback ABI inspection.
- Invoked solely on the Owner's **private workstation**, with the previously uploaded genuine OEM ELF kept off GitHub:

\`\`\`bash
python3 experiments/m3-ds3-compat-adapter/audit_oem_plugin_elf_offline.py \
  /private/path/to/m3-original-2024-libbluetooth.so
\`\`\`

The tool prints a **sanitized report**. Review even sanitized metadata before sharing to PR; never publish ELF bytes, unredacted JNI maps, BT logs or keys. Its synthetic tests use mock ELF headers only, no actual OEM bytes.

**Executed CI:** [GitHub Actions run 41468813507](https://github.com/franfran/android-bt-gamepad/actions/runs/41468813507) on \`ccef325\`: **SUCCESS**, decoded job log **17 tests, OK** for the original synthetic suite. A follow-up privacy hardening change removed any OS error-string echoes including local ELF paths (\`11d657b\`); CI status of subsequent head should be checked separately. This is **tool validation only**, not an OEM loader audit.

## I1 decision as of this increment

| Scope | Evidence-backed decision |
| --- | --- |
| Generic public Android/H618 drop-in HID Host \`.so\` | **NO_GO for known interfaces examined**. No supported plugin loader/registration/three-gate callback surface shown |
| M3 2024 **exact OEM** proprietary extension/load surface | **UNRESOLVED**. Historical hashes and native/Java observations verified, but original complete dynamic import, OEM loader and vendor package callsites not newly audited; no supported plugin contract proven |
| Kernel driver, USB dongle, BlueZ replacement, full BSP build | **OUT OF PR #52 SCOPE**. Dongle research deferred to a separate later PR; PR #51 source replacement is independent fallback only |

**Next decisive offline action:** obtain the *same already-collected private OEM ELF and JNI/APK bytes* in a session with authorized raw access and run the pinned read-only metadata scan plus explicit callsite verification. If a plausible load mechanism is found, trace its ABI to HCI/BTM/HID, Java and UHID; if not, record bounded OEM-version NO_GO with exact negative coverage. Do **not** label plugin "impossible" until OEM-specific evidence is adequate or mark the question UNRESOLVED if it is inaccessible.

No hardware runtime operations, no additional permissions granted, no plugin loaded, no changes to M3. PR #52 stays Draft.


## S7 add-on experiment is **not** an OEM-supported plugin interface

Existing [S7-C4C handoff](S7-C4C-HANDOVER.md) documents ARM32 \`dlopen\`/sandbox tests **only in independent owned/fork-owned processes** and read-only inspection of actual Bluetooth target. The target C4B snapshot explicitly recorded **\`addon.mapped=false\`**, \`injection_authorized=false\`, and unresolved live Bluetooth linker namespace/recovery. [Stage 3D addon loader script](../experiments/stage3d-addon-loader/run-on-m3.sh) itself declares "no Bluetooth process injection" and runs the loader as a separate process.

This proves that **an arbitrary executable can link/load a test add-on in its own process**, not that the OEM Bluetooth process will load a user-supplied \`.so\` by configuration or expose supported BTM/HID callbacks. Root-only remote \`dlopen\`, \`ptrace\`, linker interposition and process injection do not count as the required **supported/removable plugin interface**, and they remain outside this PR's authorized scope. Do not restart those experiments while plugin feasibility is being decided.

## Latest privacy-hardened CI confirmation

[GitHub Actions run 41469779259](https://github.com/franfran/android-bt-gamepad/actions/runs/41469779259), commit \`11d657b\`, completed **SUCCESS** after the error-path redaction fix. [Run 41469942991](https://github.com/franfran/android-bt-gamepad/actions/runs/41469942991) also **SUCCESS** at the initial report head. CI checks the mock loader-metadata logic only; original M3 2024 proprietary bytes were **not** present in runner.
