# S7-C4C-3 — Bluetooth APK and NativeLoader selection research

**Status: AOSP reference analysis + owner M3 process evidence. Runtime namespace acceptance remains UNVERIFIED; live Bluetooth injection is NO-GO.**

## AOSP evidence (not automatically applicable to OEM M3)

1. Android 12's legacy Bluetooth app is `com.android.bluetooth`, has a declared Android service and `android.uid.bluetooth` shared UID. The manifest includes service `android:process` configuration. These are **APK component declarations**, not proof of the M3's exact package layout or launch chain.
   - Android 12 reference: https://android.googlesource.com/platform/packages/apps/Bluetooth/+/refs/tags/android-security-12.0.0_r57/AndroidManifest.xml
2. ART's `libnativeloader` creates/uses a namespace associated with a classloader for JNI loads through `System.loadLibrary`. Native calls to `dlopen` or `android_dlopen_ext` are not necessarily equivalent; call origin matters.
   - https://android.googlesource.com/platform/art/+/master/libnativeloader/README.md
   - https://android.googlesource.com/platform/art/+/master/libnativeloader/native_loader.cpp
3. Read-only observation from owner M3: current Bluetooth target and its direct parent had `APP_PROCESS_BINARY` executable category; direct parent comm was classified as non-zygote, both relationships verified at the observation time. This supports further investigation of the app-process family but proves neither history of spawning nor applicable native-library namespace.

## Two distinct loader paths

| Candidate path | Initiator | What decides namespace | Evidence needed |
| --- | --- | --- | --- |
| Java/JNI load | e.g. `System.loadLibrary()` via ART | Classloader-associated NativeLoader namespace | Exact installed APK, classloader and native library directory inputs; caller identity |
| Native `dlopen()` | A call from some existing native library | Native dynamic linker context associated with call origin / namespace rules | Actual caller location, applicable linker config, runtime namespace, dependency visibility |

**There is no demonstrated production call path yet.** The test-target `rbxc4c_load` wrapper cannot be treated as a Bluetooth service symbol; its successful remote load is not evidence of either path above.

## M3-specific missing inputs (do not guess)

- Package `com.android.bluetooth` actual installed source APK path class (system, system_ext, product, vendor, apex or data); OEM may differ from stock Android 12.
- Whether `pm path` resolves one or multiple packages/code paths and whether the active Bluetooth process is bound to that APK.
- Native library loading context, classloader resolution and whether Bluetooth native stack uses JNI entry points or native direct calls for the hypothetical add-on load.
- Whether a given namespace permits the staged add-on's location and dependencies; `/linkerconfig` structural presence is not proof.

## Next safe evidence step

Collect only **sanitized classification** from an owner-operated, read-only `pm path com.android.bluetooth` lookup, with a bounded response and no raw APK path or serial in output. Cross-check the package existence and partition category; no APK extraction, no dumping private package state or raw manifest. If no confident classification is possible, emit UNKNOWN.

Even a system-installed Bluetooth APK does **not** by itself prove a JNI classloader namespace or permit `/data/local/tmp` as a load source.

## Safety and decision

No live `dlopen`, no `ptrace`, no Bluetooth restart, no package installation, no filesystem writes and no authentication-policy modifications. Existing Wi-Fi ADB remains first choice for observation; independently observed USB ADB is a last-resort safety route. **C4C-3 NO-GO** until actual caller namespace and recovery constraints are understood and separately reviewed.
