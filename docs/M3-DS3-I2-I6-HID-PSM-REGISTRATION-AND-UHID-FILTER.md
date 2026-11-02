# I2/I6 — Exact HID registration and pre-UHID input gate (pinned H618)

**Scope:** offline source inspection. No M3 device changes or approval to relax Bluetooth security. Repository source `BPI-SINOVOIP/BPI-H618-Android12` pinned `250eabfc529518b7f26432663ed0a867ab2f625d`.

## HID security registration, verified
[system/bt/stack/hid/hidh_conn.cc:95–117](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L95-L117):
`hidh_conn_reg()` registers **both** HID Control `HID_PSM_CONTROL` (0x11) and Interrupt `HID_PSM_INTERRUPT` (0x13), via `L2CA_Register2`, each with **`BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT`**. Interrupt registration failure deregisters control. [hidh_conn.cc:850–876](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L850-L876) also requests outbound control with authenticate+encrypt.

**Consequence:** the normal native HID Host path explicitly requires classic pairing/encryption for both channels. Global removal of these registration masks is NO_GO. The BTM [PSM-aware access function](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L1701-L1737) is a possible *research location* for a separate conditional cable-admission outcome, but SM4 can independently force auth/encrypt, and the callback state machine must be preserved. No safe bypass demonstrated.

## Device input path, verified
[system/bt/stack/hid/hidh_conn.cc:638–703](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L638-L703):
`hidh_l2cif_data_ind` finds HID device by incoming channel CID, rejects unknown CID / zero-byte packets, parses transaction/report type, and sends `HID_HDEV_EVT_INTR_DATA` or `CTRL_DATA` with payload toward BTA. These are **framing and routing checks, not a DS3-only report allowlist**.

[system/bt/btif/co/bta_hh_co.cc:292–305](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L292-L305):
`bta_hh_co_write(fd,rpt,len)` builds `UHID_INPUT`, checks max payload size, copies report and calls `uhid_write`. The observed generic path does **not** show DS3-specific report-type, ID, content or rate restrictions. [co.cc:474–490](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L474-L490) waits for `ready_for_data` and writes the report to kernel.

**More important:** [bta_hh_co_send_hid_info:506–539](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L506-L539) sends a peer-provided HID **report descriptor** to kernel via `UHID_CREATE`, including name/vendor/product IDs. Merely filtering input packets in `bta_hh_co_write` is **too late** to prevent a spoofed device advertising a keyboard-like descriptor or unwanted HID capabilities. The proposed bounded-risk compatibility path needs **descriptor-level validation before UHID_CREATE**, and **runtime report filtering before UHID_INPUT**, both bound to the same authorized session and device FD. Name and claimed VID:PID are not authentication.

## Specific offline test requirements
- Keep all other HID registration security flags unchanged; check correct direction and 0x11/0x13 only.
- Reject or isolate descriptor with keyboard/mouse top-level usage, composite keyboard capabilities, unsupported report IDs, unusual report sizes or inconsistent descriptor claims. Build a documented DS3 descriptor allowlist from **trusted USB baseline**; a malicious radio device can still spoof known descriptor exactly, so do not claim this cryptographically authenticates it.
- Reject oversized, malformed, unexpected type/ID, replay/out-of-epoch or post-disconnect reports **before** UHID_INPUT; ensure final kernel-facing FD belongs to authorized session. Consider failure-close and legitimate controller compatibility, not arbitrary success.
- Validate creation ordering: authorize before descriptor reaches `UHID_CREATE`, enforce per-session provenance and revoke on disconnect/virtual unplug.
- Prove native→Java event-bound admission and rollback; unchanged Java `BOND_BONDED` gate prevents use otherwise.
- Test existing wired USB RetroArch input baseline remains available; wireless PS-button connection after one USB enrollment is final acceptance.

## Verdict
**HID registration owner and two kernel-facing gateways found**: source-first integration investigation can now target exact sites without guessing. **Safety and applicability still unproven**: unknown original M3 descriptor/report formats, no trusted DS3 radio proof, no implementation of pre-auth exception, protected session bridge, complete build or runtime. This is NOT a patch authorization.

Do not silently change service flags, fake Bluetooth bond status, admit arbitrary HID descriptor, operate M3, or merge PR #50/#51/#52.
