# S7-C4C-3 — Evidence closure and engineering decision

**Decision date:** 2026-10-29  
**Decision:** **PAUSE live Bluetooth loader/injection path (NO-GO)**; close the present read-only evidence collection loop.  
**Scope:** owner-controlled Android 12 ARM32 iMETBOX M3 Bluetooth process. This document does **not** approve any live process modification, restart, attach, or linker invocation.

## Evidence ledger

| Evidence | Source | Result | Interpretation limit |
| --- | --- | --- | --- |
| Independent ARM32 loader + SVC bootstrap | PRs #3–#5, isolated owner test target | PASS | No proof for Bluetooth process context |
| Existing service status/mapping snapshots and recovery readiness | PRs #8–#9 | PASS for read-only health | Normal-state Wi-Fi ADB cannot prove recovery during hang |
| Static linker configuration | PR #11 | Candidate configurations observed | Caller namespace not identified |
| Bluetooth parent and executable provenance | PRs #13–#14 | Stable observed app_process lineage | Does not prove the loading API or ClassLoader instance |
| APK origin | PR #15 | Installed Bluetooth APK in SYSTEM | Package/process binding not proven by path alone |
| Package/process corroboration | PR #16 | Matching process name and UID 1002 | Shared UID means metadata corroboration, not unique ClassLoader binding |
| AOSP JNI reference call chain | PR #17 | Java System.loadLibrary / native JNI model documented | Historical reference cannot establish OEM mechanism |
| JNI library mapping | PR #18 | Exact libbluetooth_jni.so basename mapped from SYSTEM | Mapped != observed load call |
| JNI ELF DT_NEEDED | PR #19 | ELF32 little-endian; 8 dependencies declared | ELF metadata != actual namespace resolution |
| JNI dependency mapping | PR #20 | 8/8 basenames mapped in Bluetooth process | Duplicate basenames in APEX/SYSTEM; actual instances unverified |

The eight dependencies from owner M3 evidence are: `libbase.so`, `libc++.so`, `libc.so`, `libchrome.so`, `libdl.so`, `liblog.so`, `libm.so`, `libnativehelper.so`. Mappings are observed, not traced as load-time resolutions. `libbase.so` and `libc++.so` each occur under APEX **and** SYSTEM categories.

## Decision gates (not satisfied)

| Gate | Requirement | Status |
| --- | --- | --- |
| G1: caller context | Concrete native call site and actual linker namespace, not static candidate policy | **UNVERIFIED** |
| G2: add-on visibility | Evidence the exact add-on path + its dependencies are acceptable from that caller's namespace | **UNVERIFIED** |
| G3: independent recovery | Reproducible independent recovery from a Bluetooth linker stall, without assuming Wi-Fi or USB ADB remains available | **UNVERIFIED** |
| G4: owner authorization | Separate, explicit owner approval of a clearly bounded live-device experiment after G1–G3 | **NOT GRANTED** |

**No live Bluetooth test is authorized.** Neither library-name presence, `DT_NEEDED`, nor a positive historical `System.loadLibrary` reference can satisfy G1/G2. Normal-state USB ADB availability is not recovery evidence under failure.

## Recommended direction

1. **Stop repetitive read-only snapshots.** The M3 static/metadata evidence loop has reached diminishing returns.
2. **Prefer an isolated replica of caller conditions.** Investigate NativeLoader versus direct `dlopen` under an independently owned disposable test process, documenting which assumptions of the OEM Bluetooth launch context cannot be reproduced. Never represent replica success as proof for Bluetooth.
3. **Treat recovery as a separate engineering project.** Before any live operation, independently establish a recovery procedure with validated loss-of-service conditions and reliable out-of-band access. Until then, live testing remains NO-GO.
4. **Maintain Draft PR stack.** PRs #3 onward are research/validation artifacts, not an implicit request to merge or activate in production. The owner remains responsible for explicit authorization of any change in gate state.

## Exit condition

This decision may be revisited **only** when new, materially different evidence addresses G1, G2 and G3, followed by a specific owner review of G4. Absence of new evidence means **PAUSED/NO-GO**, not a request for another inventory script.

**Owner-facing conclusion:** The read-only campaign successfully characterized M3 Bluetooth identity, JNI mapping, ELF dependencies and their mapped presence; it did *not* establish that injecting or loading a new library into the live Bluetooth process is safe, permitted, or recoverable.
