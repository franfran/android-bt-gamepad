# Android Bluetooth Gamepad — RetroBox DS3 on M3

**Research snapshot / engineering handover (2026-10-28)**. Goal: support a wireless Sony DualShock 3 (DS3, USB VID:PID `054c:0268`) as an Android 12 gamepad on a rooted iMETBOX M3 while preserving unrelated Bluetooth security.

**Actual outcome:** DS3 **works over USB** in Android/RetroArch after an autoconfig adjustment. **Wireless pairing is not working.** A series of isolated ARM32 process experiments passed on the M3, but **no inert add-on has been injected into the real Bluetooth process** and no DS3 compatibility fix has been shipped.

## Start here

1. [Project state / test matrix](docs/STATUS.md): precisely what was tested on hardware and what was not.
2. [S7-C4C engineering handover](docs/S7-C4C-HANDOVER.md): blockers, required source modules, acceptance criteria and recovery design.
3. [System architecture and HCI findings](docs/ARCHITECTURE.md): why USB success differs from Bluetooth and why the kernel L2CAP experiments were insufficient.
4. [Safety / rollback](docs/SAFETY.md): **DO NOT RUN** the obsolete Bluetooth `inject` prototype or modify the system Bluetooth `.so`.
5. [Source/build notes](docs/BUILD-AND-TEST.md): repository contents and how to reproduce the read-only checks without an Android NDK on Mac.

### Repository map

- `experiments/s7-c4b/` — latest **read-only** integrated address/PID/checksum validation, with tests. **Not an injector.**
- `experiments/s7-c4a/` — add-on staging (verified SHA-256), no injection.
- `experiments/s7-c3-resolver/` — latest v3 ARM32 ELF/Thumb address resolver; older buggy versions intentionally omitted.
- `experiments/s7-c1/` — M3-PASS isolated target-owned scratch + remote `dlopen` test (fork-owned child only).
- `experiments/s4/`, `experiments/s5/` — isolated remote allocation and multithreaded `dlopen` foundations.
- `experiments/s7-c3d/`, `experiments/s7-c3e/` — constructor delays, concurrent `dlopen` observations and fail-closed policy.
- `experiments/stage3c-policy/`, `research/` — original DS3-scoped policy design, stack/disassembly audits and other findings.
- `evidence/` — selected device evidence; raw HCI snoop, pairing logs and extracted vendor APK/SO remain off-repository.
- `AGENTS.md` — working instructions for the next developer / AI agent.

Some checked-in ARM32 files are **experimental prebuilt binaries**, not a release. C/Java/Python source and tests are retained so the engineering history is not lost. Build instructions in individual experiments reflect their original state. No production-ready S7-C4C code exists yet.

**Security constraint:** Any future DS3 exception must be limited to a physically USB-enrolled controller and inbound HID Control/Interrupt (PSMs `0x11`/`0x13`). Never globally bypass Bluetooth authentication, manufacture LinkKeys, or infer enrollment from a device name alone.
