# M3 DS3 compatibility adapter — architecture investigation

Status: **research only / NO_GO for runtime deployment**. Branch: `research/m3-ds3-compat-adapter` from `main`. Independent of Draft PR #51 (source-first Fluoride patch) and Draft PR #50 (reverse-engineering archive).

## Objective
Determine whether genuine Sony DualShock 3 wireless support can be added to rooted iMETBOX M3 / Android 12 through a minimal, removable compatibility adapter **without replacing OEM `/system/lib/libbluetooth.so`**. Preserve native Bluetooth behavior for other devices. Do not assume Android has a loadable Bluetooth HID plugin interface.

## Facts transferred from existing work
- M3: Allwinner H618, Oranth Android 12 / API 31, ARM32 Fluoride. OEM `libbluetooth.so` ELF32 ARM; Bluetooth process `com.android.bluetooth`, UID 1002.
- Wired DS3 already **works fully** in RetroArch; USB sixpair enrollment completed. Wireless remains unsuccessful.
- **Gate A (native):** Classic HID L2CAP PSMs 0x11 / 0x13; native auth/encryption admission; observed HCI Authentication Failure 0x22. Existing sixpair enrollment does not prove a normal Bluetooth bond.
- **Gate B (Java):** OEM `HidHostService.okToConnect()` requires BOND_BONDED (12) and acceptable connection policy; rejected connection may trigger virtual-unplug.
- **Gate C (kernel):** M3 `CONFIG_UHID=y`, `CONFIG_HID_SONY=y`; kernel hid-sony may require wireless feature SET_REPORT F4 completion. Fluoride source/native evidence shows missing UHID SET request-ID association and a log-only `bta_hh_co_set_rpt_rsp`. This is **not** the first observed blocker, and a reply cannot be fabricated.
- Matching public source: BPI-SINOVOIP/BPI-H618-Android12 commit `250eabfc529518b7f26432663ed0a867ab2f625d`; system/bt tree `d6f07310f73694977b301eac63d67b219ca20625`. Strong structural match, **not** OEM ABI proof.
- PR #51 S9 integration is an offline prototype and **does not** issue UHID SET_REPORT_REPLY. S17 records that a complete ARM32 BSP build and OEM ABI comparison have not yet succeeded.
- Historical S7-C4C live injection readiness remains **NO_GO**. No live hooking, injection or weakening Bluetooth security.

## Candidate architectures — hypotheses, not decisions

| Candidate | Concept | Primary feasibility test | Risk |
| --- | --- | --- | --- |
| A. In-process native adapter | Find a supported Fluoride/OEM extension hook and implement only DS3 policy/SET transaction handling in a module | Source-level search for stable callbacks/plugin registration, load path, ownership and ABI | No supported extension may exist; injection is NOT an acceptable fallback |
| B. Independent native daemon | Own DS3 Classic HID transport and bridge input via UHID or uinput | Can it obtain an authorized HID transport without stealing the live controller/HCI/PSM ownership from Fluoride? | Second stack conflicts; native auth remains; lifecycle/control access |
| C. Minimal source adapter | Small, audited Fluoride change that calls a segregated DS3-specific component | Determine minimal callsites and whole-stack rebuild/link requirements | Still modifies system stack; Java gate separate |
| D. Existing supported APIs/config | OEM/system Bluetooth policy API or configuration sufficient for DS3 | Trace real source callsites, privileges and behavior; avoid global low-security toggles | No suitable per-device policy exposed |

## Investigation milestones and decision gates
1. **I1: Extension surface inventory.** Map Android 12 Fluoride `btif`, `bta/hh`, `stack/hid`, JNI and Java HID Host boundaries. Identify real registration/callback/dlopen/module hooks (with pinned source links), and distinguish vendor HAL from HID host extension.
2. **I2: Controller ownership and security.** Document exclusive HCI/L2CAP ownership and whether *supported*, per-device cable-enrolled legacy HID admission can occur without global authentication downgrade. Disallow spoofable MAC-only authorization. Use offline diagrams/tests first.
3. **I3: Kernel/input bridge.** Verify UHID versus uinput kernel configuration, access controls, Android InputReader recognition, joystick axes, battery/rumble and disconnection lifecycle. `CONFIG_UHID=y` alone does not prove `uinput` availability.
4. **I4: Java policy.** Map bond and connection-policy enforcement and virtual-unplug semantics; determine whether legitimate independent transport bypasses Java service or just creates a conflicting session.
5. **I5: Latency/reliability.** Specify monotonic event timestamps, HID report-to-input processing P50/P95/P99, dropped/reordered packets, reconnect, CPU and controller contention. P95 under 1 ms is only a **provisional software-hop target**, not measured.
6. **I6: Decision record.** Explicit GO / CONDITIONAL / NO_GO for A–D, smallest viable proof-of-concept, security impact, rollback and comparison with PR #51 patched-library design.

## Acceptance criteria
Every positive feasibility claim must link concrete pinned source code or reproducible **offline** host evidence. Separate **PROVEN / INFERRED / UNTESTED**. Report no-feasible-plugin outcome if warranted. No architecture should claim to fix all three gates without addressing each separately.

## Safety boundary
No changes to the M3 device, root/HCI runtime probes, Bluetooth restart, binary injection, APK swap, firmware flashing, /system writes, SELinux/AVB bypass, global security weakening, unauthorized connection attempts, or deployment without separate, explicit Owner approval. PR #50 and PR #51 remain independent and unmerged. Keep hardware identifiers, link keys, private dumps and other secrets out of public GitHub history.

## Primary sources
- [Draft PR #51 source-first](https://github.com/franfran/android-bt-gamepad/pull/51)
- [PR #51 handoff](https://github.com/franfran/android-bt-gamepad/blob/feat/m3-ds3-source-first/docs/M3-DS3-SOURCE-FIRST-HANDOFF.md)
- [PR #51 S17 build/ABI blocker](https://github.com/franfran/android-bt-gamepad/blob/feat/m3-ds3-source-first/docs/M3-DS3-S17-REAL-BUILD-BLOCKER-ABI-GATE.md)
- [Draft PR #50 reverse-engineering evidence](https://github.com/franfran/android-bt-gamepad/pull/50)
- [Pinned public H618 Android12 BSP](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/tree/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt)

## Next action
Perform I1 source-only extension-surface inventory, then I2. **Do not start daemon implementation** until controller ownership and legitimate per-device authentication are explained.
