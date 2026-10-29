# M3 status and validation matrix — 2026-10-28

## Hardware / software (measured)

- Android 12, API 31, ARM32 / `armeabi-v7a`; `su` installed at `/system/xbin/su`, root command form `su 0`.
- Bluetooth process `com.android.bluetooth` (comm `droid.bluetooth`), UID 1002, SELinux domain `u:r:bluetooth:s0`; observed 48–49 threads and permissive mode. PID **changes across restarts** (e.g. 669, 675, 671); never pin a PID or ASLR address.
- `libbluetooth.so` `/system/lib/libbluetooth.so`, `libbluetooth_jni.so`, Bionic `libdl.so` under `/apex/com.android.runtime/lib/bionic/`, 32-bit linker under `/apex/com.android.runtime/bin/linker`.
- Bluetooth HAL via `android.hardware.bluetooth@1.0-service`, AIC UART `/dev/ttyAS1`; no kernel `hci0` even though kernel Bluetooth sockets can be opened/bound.
- Runtime flags show `gd_security=false`, `gd_l2cap=false`, `gd_hci=false` etc; this device uses the **legacy** Fluoride paths relevant to Stage 3C.

## Controller behavior (measured)

- Sony DS3 `054c:0268` USB recognized by Android as GAMEPAD/JOYSTICK (`/dev/input/event3` observed). RetroArch `com.retroarch.ra32` worked in menus with custom Android autoconfig profile (device name `Sony PLAYSTATION(R)3 Controller`).
- USB `sixpair` set DS3 master to M3 Bluetooth adapter. Pressing PS leads to L2CAP HID Control (`PSM 0x11`) connection attempt and legacy authentication flow.
- Android responds to PIN Code Request; the 6-byte adapter-address PIN was submitted at HCI level but `Authentication Complete` returned **0x22 / LMP Response Timeout** ~30 seconds later; `BOND_BONDING → BOND_NONE`. No proof of established LinkKey/bond.
- Generic PIN guessing is not a productive path. HDMI/RetroArch cannot fix authentication in the Bluetooth stack.

## Development tests (actual M3 outputs)

| Stage | Measured result | Scope and limit |
|---|---|---|
| Kernel L2CAP stage0–2 | `socket` / `bind` success | Does not prove kernel owns HAL HCI traffic |
| D2a | `dlopen` / `dlclose` PASS | Own isolated process |
| D2b-2a, 2b | `ptrace` attach and read/write/restore PASS | Fork-owned child |
| D2b-2c | Remote `dlopen` and maps PASS | Fork-owned child |
| D2b-2d-A | Bluetooth leader thread SEIZE/INTERRUPT/DETACH PASS | No register changes/injection |
| S1 | 4 workers progressed after attach/detach PASS | Owned child |
| S2 | Remote function returned `42`; 250ms simulated timeout recovery PASS | Owned child, simple function |
| S3 | Guard pages, scratch canaries, timeout recovery PASS | Parent/child owned mapping |
| S4 v2 | Remote `mmap2` / `mprotect` / memory checks / `munmap` PASS | Child-owned mapping |
| S5 | Multi-thread remote `dlopen`, add-on mapped, workers 4/4 PASS | Fork-owned child |
| S6, S7-A/B | Read-only process/evidence validation PASS | Does not authorize injection |
| S7-C1 | Remote private scratch + path + `dlopen` + `munmap`; workers 4/4 PASS | Fork-owned child |
| S7-C3 v3 | ELF/PT_LOAD/Thumb `dlopen` resolver PASS | Read-only Bluetooth PID |
| S7-C3b/c | Identity/thread checks PASS; recovery state-machine locally tested | Real linker recovery untested |
| S7-C3d | 450ms constructor delay PASS; 3500ms stalled constructor quarantined | Owned process, not a mutex proof |
| S7-C3e v2 | B finished before A constructor in both cases; normal and timeout policy PASS | Owned process; does not prove absence of linker locks |
| S7-C4A v2 | Add-on SHA-256 matches staged bytes; PID unchanged PASS | Add-on staged, **not loaded** |
| S7-C4B | Read-only integrated resolver/checksum PASS; `inspection_issues=[]` | `addon.mapped=false`, `injection_authorized=false` |
| S7-C4C-1/2 v3 (PR #3) | **M3 PASS (2026-10-28)** | Separately started 48-worker test target, target-private mmap/guard/RW/RX trampoline, negative/positive dlopen, remote dlerror, canaries, worker progression, munmap; bootstrap uses test-target compiled trap only |
| S7-C4C SVC bootstrap (PR #4) | **M3 normal-path PASS (2026-10-28)** | Independent 48-worker test target; ARM SVC syscall-stop bootstrap, guard/RW/RX scratch, positive/negative test dlopen/dlerror, worker progress, munmap, cleanup; signals/timeouts untested; Bluetooth NO-GO |

Raw results shared by operator are authoritative over README files written before each M3 test. `evidence/` contains selected audit JSON snapshots, not the full raw logs.

## S7-C4C-1/2 real-device closeout (2026-10-28)

Operator ran `experiments/s7-c4c/run-on-m3.py` v3 (PR #3) and supplied the complete M3 stdout. Measured: `TARGET READY: PID=4423, 48 workers, identity verified; ADB session alive`; `TARGET_IDENTITY_CONFIRMED; load_bias=0x03a71000`; target-private `MMAP2 OK`; `RX RETURN TRAMPOLINE VERIFIED`; missing library `DLOPEN NULL` plus nonempty `DLERROR`; inert test module mapped; canaries intact; background workers progressed; remote `MUNMAP` completed; `PASS: non-fork independent ARM32 target call`; test-only cleanup complete. PID/base are **snapshots**, not reusable constants.

**Interpretation:** cross-process loader parity proven in a separately started, instrumented ARM32 test process on M3. The initial bootstrap still relies on a BKPT symbol compiled into that test target, and its success does not establish an arbitrary-process bootstrap, Bluetooth linker namespace, a recovery procedure for stalled real Bluetooth `dlopen`, or wireless DS3 pairing. Live Bluetooth injection remains NO-GO. Earlier v1/v2 startup failures were not remote-call failures; v3 switched to a persistent ADB foreground target session and target-written PID.

## PR #4 SVC bootstrap: normal-path M3 PASS (see measured trial below)

The stacked `feat/s7-c4c-svc-bootstrap-test` branch proposes target-image
ARM `SVC` syscall-stop bootstrap to eliminate dependency on the special
test-target return trap for initial memory allocation. **Normal path verified
on M3** (details below). PR #3's earlier M3 PASS remains separately attributed
to the original trap bootstrap. No Bluetooth execution or DS3 pairing change is authorized.

## PR #4 SVC bootstrap independent-target M3 trial (measured, 2026-10-28)

Operator used the **corrected six-file test artifact** from GitHub Actions run
`40802426406` (artifact `12865984164`) and ran
`python3 run-on-m3.py <ADB_SERIAL>` on an owner-controlled M3. The full stdout
was supplied in chat and records:

```text
TARGET READY: PID=2963, 48 workers, identity verified; ADB session alive
TARGET_IDENTITY_CONFIRMED; load_bias=0x0faf8000
TEST IMAGE ARM SVC BOOTSTRAP SELECTED
TARGET-PRIVATE MMAP2 OK
TARGET-OWNED RX RETURN TRAMPOLINE VERIFIED
EXPECTED MISSING LIBRARY: DLOPEN NULL
REMOTE DLERROR CAPTURED (nonempty)
TEST MODULE LOADED IN INDEPENDENT TARGET; CANARIES VERIFIED
BACKGROUND WORKERS PROGRESSED WHILE LEADER TRACED
REMOTE MUNMAP COMPLETED VIA TARGET-IMAGE SVC BOOTSTRAP
PASS: non-fork independent ARM32 target call, RX trampoline, dlopen negative/positive, cleanup
S7-C4C-1/2 INDEPENDENT TARGET = PASS (NOT Bluetooth authorization)
TEST-ONLY CLEANUP COMPLETE
```

**Measured:** test-process normal path PASS with SVC-stop bootstrap, private
mapping, return trampoline, library load/error handling, active workers and
scoped cleanup. The program uses tagged `PTRACE_SYSCALL` entry/exit stops and
restores leader registers, but stdout does **not** include detailed per-stop
register dumps, explicit signal-delivery simulation, or a forced timeout.
PID and load-bias above are historical snapshots only.

**Still untested:** unexpected signals or timeout while syscall/linker is
active, arbitrary library namespace in Android Bluetooth, and any actual
Bluetooth process execution/recovery. SVC site selection is confined to the
controlled test executable, and `dlopen` still calls test-specific wrapper
symbols. **Do not promote PR #4's pass to production S7-C4C approval.**
