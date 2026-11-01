# M3 DS3 Native Pre-Authentication Context — Existing S8 Evidence Reconciled

**2026-10-31. Offline-only consolidation.** No live Bluetooth changes, no new original ELF disassembly; this draws directly on original-M3 SHA-pinned S8 PR #32/#33/#37/#38/#39/#40.

## Major positive finding: both peer address and PSM exist at the pre-auth caller

Owner-original M3 `libbluetooth.so` (SHA256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`) has a Classic L2CAP incoming connection-security route:

- `l2c_csm_execute` CLOSED-state event 10 (`L2CEVT_L2CAP_CONNECT_REQ`) routes through the real TBH dispatch; Classic branch chooses `btm_sec_l2cap_access_req`, as established by PR #38.
- Candidate B, `0x2897b4: bl 0x258e68`, invokes `btm_sec_l2cap_access_req` with the **actual remote address pointer** from connection record `[r10+0x2c]+0x20` and the **actual PSM** loaded from service-record `[r10+0x38]+0x02`. The directional argument is `is_originator=0`. These are direct original M3 disassembly findings in PR #32.
- The call returns `BTM_CMD_STARTED` candidate status 1, leading to a pending peer connect response (`l2cu_send_peer_connect_rsp` at `0x2897c4`), PR #33.
- Downstream `btm_sec_l2cap_access_req_by_requirement` does **not** retain an independently passed PSM. A future narrowly scoped decision requires a caller that still has channel PSM and peer identity; filtering only by address or patching the by-requirement callee in isolation would be unsound.
- Separate S8 PR #39/#40 establish a conditional route through `btm_sec_execute_procedure` to HCI Authentication Requested opcode `0x0411` and general failure handling for status `0x22`. These are static paths, **not a live execution trace for the user’s DS3 attempt**.

## Consequences for the implementation

**Positive:** The required peer identity + HID PSM + inbound-direction context already coexist in an earlier native security caller. This reduces the need for speculative invasive context reconstruction or adding a general PSM field to lower-level state, and gives a concrete location for evaluating a DS3-only policy in a **source-level/offline** design.

**Still missing / critical caution:** A matching native argument signature is **not** a supported dynamic hook, and the actual device-specific runtime branch, hook safety, ownership and recovery are not demonstrated. A MAC address is spoofable and insufficient as proof of physically authorized enrollment. The user’s already-completed USB enrollment can establish an owner-approved local allowlist, but stronger trust/report restrictions are still required. Nothing here authorizes overriding authentication or altering a registered global HID security mask `0x36`.

## Exact Android second gate

Actual M3 `Bluetooth.apk` is SHA verified `d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f`. Its `HidHostService.okToConnect` at DEX `0x26e880` requires `BOND_BONDED`; its actual `HidHostService$1.handleMessage` code (DEX `0x26dc8c`) invokes that check for initial CONNECTED transition in message case 3. This is a **second downstream gate**, separate from native auth.

A one-stage PIN helper or a one-stage native exception will not satisfy both conditions. The safe design review must cover both, preserving normal Bluetooth admission rules for every unrelated device.

## Implementation decision / gates

- **Architecture-level GO:** Offline feasibility of per-enrolled-controller, inbound HID PSM 0x11/0x13-only handling at the **caller retaining both address and PSM**, plus an explicit Java HID Host authorization model. Review BlueZ 5.83's early low-security listening behavior carefully, since it is not itself strictly per-MAC at the earliest stage.
- **Integration-level UNVERIFIED:** No public Android API or OEM plugin extension has yet been shown to let a standalone APK control the native security result at this point. Root permissions, a Java broadcast receiver or the presence of function arguments do not supply a safe hook.
- **Deployment NO_GO:** No native injection, service restart, APK overwrite, system signing workaround, fake bonds/LinkKeys, global Bluetooth downgrade or actual pairing test without explicit scoped owner approval and independent recovery checks.
- **Next limited offline experiment:** A C/C++ pure host harness may model a hypothetical decision predicate and its interaction with the native security status + Java gate, asserting all non-DS3 cases preserve original behavior. Such a harness does not establish deployability.

## Objective

Already completed: one-time USB sixpair enrollment of M3 host address, wired DS3 Android input/RetroArch PASS. Final desired outcome: unplug DS3; press PS; M3 built-in Bluetooth accepts only the owner-enrolled controller; wireless Android InputDevice and RetroArch buttons work reliably, including reconnect. No repeated USB functionality testing.

References: https://github.com/franfran/android-bt-gamepad/pull/32 , /pull/33 , /pull/38 , /pull/39 , /pull/40 ; https://github.com/franfran/android-bt-gamepad/pull/50 .
