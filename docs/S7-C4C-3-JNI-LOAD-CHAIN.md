# S7-C4C-3 — Bluetooth JNI load-chain evidence and caller namespace

**Status:** static AOSP research only. Production Bluetooth loader permission and recovery remain **UNVERIFIED / NO-GO**.

## AOSP reference chain, Android 12-era legacy Bluetooth

The legacy Bluetooth Android app defines a `Bluetooth` APK and links `libbluetooth_jni` as `jni_libs` in its Soong `Android.bp`. Its Java `AdapterService` uses `System.loadLibrary("bluetooth_jni")` to load the JNI bridge (exact location/timing varies by Android release). These two independent source artifacts support this *reference chain*:

```text
Bluetooth APK Java service
  -> System.loadLibrary("bluetooth_jni")
  -> ART / libnativeloader for classloader-aware JNI loading
  -> libbluetooth_jni.so (Java/native bridge)
  -> Bluetooth native stack / linked dependencies
```

References:
- Legacy Bluetooth app build: https://android.googlesource.com/platform/packages/apps/Bluetooth/+/b38e2d98eb228593a909f9ba301192397dab8208/Android.bp
- Legacy Java AdapterService: https://android.googlesource.com/platform/packages/apps/Bluetooth/+/aa90f0c/src/com/android/bluetooth/btservice/AdapterService.java
- ART NativeLoader: https://android.googlesource.com/platform/art/+/master/libnativeloader/README.md

**Version caution:** The quoted Java source is an illustrative historical revision, not proof that the owner's OEM Android 12 build includes identical Java code. Current Mainline Bluetooth app sources differ substantially; do not interchange them with legacy Android 12 evidence.

## M3-specific corroboration already measured

- Installed `com.android.bluetooth` APK exists in SYSTEM partition (one package path).
- Running Bluetooth process and observed parent executable both categorized `APP_PROCESS_BINARY`; process name matches package name.
- Installed package UID 1002 matches active Bluetooth process UID 1002, with shared-UID ambiguity clearly retained.
- Prior read-only maps established `libbluetooth.so` mapped in the active process; no owner-provided map evidence *yet* specifically establishes `libbluetooth_jni.so` or its load location.
- Android linkerconfig policy files exist; actual Bluetooth caller namespace was not measured.

## Separate the questions

| Question | Current evidence class | Answer |
| --- | --- | --- |
| Does a reference Bluetooth APK use JNI bridge loading? | AOSP source | Yes, reference source uses `System.loadLibrary` |
| Is M3 Bluetooth the installed system APK process? | M3 metadata corroboration | CORROBORATED, not a unique classloader binding proof |
| Is `libbluetooth_jni.so` currently mapped in M3? | No specific sanitized M3 report | UNVERIFIED |
| Did M3 load JNI using ART NativeLoader? | Source analogy only | INFERRED / UNVERIFIED runtime |
| What namespace governs an **arbitrary new** native `dlopen` call? | No caller-context evidence | UNVERIFIED |
| Is the staged inert add-on path permitted and dependencies visible? | No service-context check | UNVERIFIED |
| Can recovery reverse an in-flight linker stall? | Not established | NO-GO |

**Key distinction:** a successful historical `System.loadLibrary("bluetooth_jni")` for a system-provided library does *not* prove a future direct native `dlopen` of an add-on from `/data/local/tmp` is allowed. The linker may choose a caller-associated namespace, while ART NativeLoader's JNI load path is classloader-aware.

## Bounded next evidence, without execution

A targeted read-only check of current process mappings can answer **only** whether the exact library basename `libbluetooth_jni.so` is mapped and classify its containing filesystem partition (SYSTEM, SYSTEM_EXT, VENDOR, APEX or OTHER). Match entire path basenames to avoid substring confusion. Output only sanitized booleans/categories (no raw mapping text, PID, addresses, APK private data). Validate process identity before/after, and mark mapping changes as inconclusive. No attempt to inspect internal linker data structures or execute loaders.

If JNI mapping is absent, do **not** claim the service is uninitialized: OEM builds may link differently. If present, treat it as evidence of library mapping, **not** of a namespace used by an imagined add-on call.

## Decision

Maintain C4C-3 **NO-GO** for live Bluetooth injection and restart. Separate review and owner approval are required before any recovery or execution experiment. Prefer Wi-Fi ADB for the read-only investigation, USB only as last resort.
