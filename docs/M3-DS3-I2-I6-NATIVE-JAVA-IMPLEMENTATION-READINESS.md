# I2/I6 — Native+Java CablePairing feasibility decision after kernel config recovery

Pinned tree: `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. **Source-review outcome, not a working patch or Owner approval for runtime security exceptions.**

## Current concrete facts
- Owner-provided kernel config shows `CONFIG_HID_SONY=y`, `CONFIG_UHID=y`, Classic HIDP enabled. This **removes a kernel configuration blocker**, not the upstream native/Java authentication blockers or uncertainty of Bluetooth Sony driver attachment.
- [`hidh_conn.cc:95–117`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L95-L117) registers BOTH HID PSM 0x11/0x13 with `BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT`.
- [`btm_sec.cc:1701–1737`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L1701-L1737) retains peer/PSM/direction when it resolves the service security record. It then passes only security flags + peer/direction/callback to `btm_sec_l2cap_access_req_by_requirement`. [`btm_sec.cc:1488–1680`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L1488-L1680) can impose additional SM4 authentication/encryption.
- [`HidHostService.java:185–207`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L185-L207) handles CONNECTED asynchronously and invokes `virtualUnPlugNative` on rejected incoming peer. [`:892–919`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L892-L919) enforces BOND_BONDED, quiet mode and connection policy. PR #50 also corroborated actual OEM Java gate.
- BTA HID handle reaches BTIF but HAL/JNI connection-state callback drops handle/epoch and sends address+state only. L2CAP LCB can be reused during reconnect. A Java query by address alone is insufficient.
- HID descriptor enters UHID_CREATE via `bta_hh_co_send_hid_info`; reports reach UHID_INPUT via `bta_hh_co_write`. Exact owner Bluetooth descriptor and validated report allowlist remain absent.
- PR #50 BlueZ 5.83 cable-pairing reference demonstrates a bounded-risk exception, **not proof against spoofed radio MACs**.

## Feasibility triage
| Candidate | Current verdict |
|---|---|
| Load Sony HID kernel module or rebuild just to enable Sony+UHID | NOT NEEDED per supplied config, runtime binding unproven |
| USB 0xF5 write alone | Insufficient: only sets controller target host address |
| Privileged PIN receiver or guessed PIN | NO_GO; does not implement nonbonded cable HID admission |
| Global HID registration mask change | NO_GO; exposes unrelated devices, SM4 may still enforce auth |
| Per-PSM BTM source-only bypass returning success | NO_GO AS PATCH: callback/session semantics and input isolation not proven |
| Source-integrated per-session Native+Java CablePairing with descriptor/report restrictions | DESIGN CANDIDATE; multiple unresolved guarantees and buildability |
| Standalone drop-in `libbluetooth.so` as a complete solution | NOT ESTABLISHED: Java admission and UHID SET_REPORT remain separate |

## Bounded next **implementation readiness** decision
**GO only for offline code and test prototype**, not target runtime. Implementation-oriented next increment should be:
1. A pure source-independent policy predicate with **explicitly separate** USB provenance, claimed radio address, ACL epoch/PSM binding, owner-approved bounded-risk selection, revocation, and descriptor/report eligibility. Do not use the earlier symbolic `trusted_peer_proven=True` as a production oracle.
2. Mock the BTM caller/callback lifecycle, including successful, pending and negative status, and ensure ordinary HID security decisions are untouched for unknown devices/PSMs; never synthesize fake authenticated/encrypted flags. Use tests to explore whether a distinct `CABLE_AUTHORIZED` state can propagate without inventing an official BTM security status.
3. A separate Java policy evaluation model that preserves quiet mode and forbidden policy; reject stale event generations. **No Java MAC allowlist.**
4. Once source integration design passes negative testing, review complete Android build/Bluetooth.apk/native ABI deployment constraints and recovery gate. PR #51 full BSP remains unavailable on the owner-reported host and is NOT silently assumed ready.
5. Explicit Owner security-risk acceptance and separate permission required before any on-device test or security policy change.

## Stop conditions
- No end-to-end event-bound native-to-Java grant.
- Bluetooth unauthorized HID capability/reports can reach kernel before filtering.
- Changes affect non-DS3 registered security.
- Source cannot build in a matching M3 system image / cannot be safely rolled back.
- Unknown provenance is silently treated as cryptographically authenticated.

**Decision:** kernel config evidence gap closed. Source integration feasibility remains **conditional / not proven**. Keep PR #52 Draft and PR #50/#51 independent; no device operations authorized. Owner final acceptance stays wired-once enrollment followed by repeatable wireless RetroArch use.
