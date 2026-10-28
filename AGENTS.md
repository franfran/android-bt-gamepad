# RetroBox Android Bluetooth Gamepad — agent handoff

Read `README.md`, `docs/STATUS.md`, `docs/S7-C4C-HANDOVER.md`, and `docs/SAFETY.md` before making changes.

- Device: rooted iMETBOX M3, Android 12 / API 31, ARM32 / armeabi-v7a, legacy Fluoride; `su 0` works, `su -c` does not. Bluetooth service `com.android.bluetooth`, process comm `droid.bluetooth`, UID 1002. SELinux observed Permissive during experiments.
- Project goal: wireless DS3 -> Android InputManager -> RetroArch. USB already works; wireless still fails after legacy PIN and HCI auth timeout `0x22`.
- Keep **measured** versus **inferred** versus **untested** clearly labeled. In particular S1–S5 and S7-C1 succeeded ONLY in child processes; S7-C3 and C4B are read-only target inspection.
- Do not repeat prior generic `ptrace`/socket probes. Work toward a demonstrably safe target-side execution/return mechanism and linker namespace experiment.
- Never enable or reuse the historical `bt_inert_inject` path. Do not write to `/system`, change SELinux, edit Bluetooth bond DB, change global auth policy, install boot injection, or initiate unattended Bluetooth process injection.
- For real Bluetooth execution, require a reviewed operator-controlled one-shot plan and verified independent recovery before touching a live process. Interrupted `dlopen` cannot be safely rolled back merely by restoring CPU registers.
- Dynamic PID/ASLR every session, check process identity and thread count, verify target ELF build/hash and executable mapping, use Thumb function pointers where required.
- No Android NDK on operator Mac. Prefer prebuilt ARM32 executables or provide sandbox/reproducible CI build; do not ask operator to install NDK as a prerequisite.
- Do not commit raw snoop logs, LinkKeys, adapter/controller MACs, real home IPs, extracted proprietary Bluetooth binaries, or credentials. Sanitized source and selected evidence only.
- Favor PRs, tests and small verifiable milestones. Owner reviews before merge.
