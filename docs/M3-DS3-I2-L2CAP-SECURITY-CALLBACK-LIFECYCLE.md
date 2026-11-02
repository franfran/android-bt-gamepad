# I2 — L2CAP security callback lifecycle and DS3 cable-enrollment state hazards

Source pin `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. Source-only analysis; no M3 test.

## Exact callback source
[system/bt/stack/l2cap/l2c_link.cc#L266-L325](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_link.cc#L266-L325):
1. `l2c_link_sec_comp` forwards `p_bda`, `transport`, original `p_ref_data`, `tBTM_STATUS` to `l2c_link_sec_comp2`.
2. `BTM_SUCCESS_NO_SECURITY` is normalized to `BTM_SUCCESS` at lines 284–286. **This normalization is existing status handling, NOT a secure per-device cable-enrollment authorization API.**
3. Finds current LCB by peer address **and transport**. If absent, logs and returns.
4. Iterates current LCB channel queue and compares `p_ccb == p_ref_data`. If no matching channel, no state transition occurs. Pointer match is only a current-channel existence check, **not proof of identity, generation, or absence of stale-pointer reuse**.
5. On `BTM_SUCCESS` emits `L2CEVT_SEC_COMP`; on `BTM_DELAY_CHECK` arms delay timer; otherwise emits `L2CEVT_SEC_COMP_NEG`.

[system/bt/stack/l2cap/l2c_csm.cc#L445-L528](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_csm.cc#L445-L528) accepts or rejects the peer-initiated channel in `CST_TERM_W4_SEC_COMP`. Success proceeds to `CST_W4_L2CA_CONNECT_RSP` and classic connect response/configuration (if not waiting on info); failure sends `L2CAP_CONN_SECURITY_BLOCK` and releases the channel; disconnect aborts outstanding BTM access and releases CCB.

## Scope and hazards for a hypothetical adapter
- Avoid putting an unconditional `BTM_SUCCESS_NO_SECURITY` bypass in the L2CAP caller: semantics of existing security registrations/callbacks, other PSMs and unknown devices must be preserved.
- Track separately a **trusted owner-controlled cable enrollment record** and **ephemeral L2CAP connection/session authorization**; neither MAC nor `p_ccb` pointer is cryptographic controller proof.
- The actual code's callback match lacks a session epoch/generation token. Channel memory reuse, race between two channels, duplicate callback and delayed completion require a separate proven safe lifecycle before any GO.
- *Control-first* PSM 0x11 and subsequent interrupt PSM 0x13 admission must refer to the same verified session; disconnect/revoke stops admission and retires all outstanding authorization. The order requirement is part of proposed adapter contract, not proof every upstream packet arrives in that sequence.
- Outbound classic callsites also exist; ensure the adapter is not inadvertently enabled on all directions.
- Java HID Host must receive a separate protected admission signal for exactly the authorized cable-paired session without falsifying `BOND_BONDED`. Only native patching remains incomplete.
- Kernel UHID SET_REPORT gap is a later stage and remains tracked separately in PR #51.

## Owner acceptance invariant
**Already validated** DS3 USB gameplay works with M3/RetroArch. **Approved user workflow** one-time USB cable enrollment, then remove cable, press PS button and reconnect/play wirelessly without re-enrollment (including after normal M3 reboot). Working USB alone is not proof of wireless bond/authorization.

## Offline test matrix before implementation GO
1. No enrollment; wrong peer; spoofed name/CoD; mismatched current adapter; revoked record => reject.
2. Correct enrollment but unrelated PSM, outgoing direction, different controller/host, keyboard profile => original default security path.
3. Authorized control channel before interrupt, interrupt-only, simultaneous channels, duplicate request => deterministic fail-closed session rules.
4. Disconnect while auth pending, reused CCB pointer, stale callback from earlier epoch, link reset, reboot => never advance a different session.
5. `BTM_SUCCESS_NO_SECURITY` must not be conflated with actual link encryption/authentication or an approved policy decision.
6. No Java authorization until matching native cable-enrollment session is established; preserve quiet-mode and forbidden-policy decisions.
7. No fabricated UHID completion or GET/SET transaction ID reuse.

## Verdict
**Source callback semantics: VERIFIED.** **Safe adapter authorization semantics and session lifecycle: NOT YET PROVEN.** No implementation GO. Keep PR #50 reverse-engineering archive and PR #51 source-first patch independent, both unmerged. No runtime M3 actions, pairing, restarting, privileged daemon, global security change, or linking raw identifying logs to public GitHub.
