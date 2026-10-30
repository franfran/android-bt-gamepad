# S8 — M3 CSM incoming-security predecessor: actual channel attribute branch

**Date:** 2026-10-29. **Input:** owner-uploaded original 32-bit ARM M3 `libbluetooth.so` (SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`). Analyzed privately and read-only; original binary not committed. Addresses below are ELF VMAs, not runtime addresses or patch offsets.

## Actual incoming candidate B predecessor

We can now demonstrate a **direct control-flow branch** into the previously verified incoming security path `0x2897b4`, rather than treating proximity of a diagnostic event table as evidence.

```asm
0x28867a  ldr.w r0,[r10,#0x2c]   ; channel's connection record
0x28867e  ldrb.w r1,[r0,#0xc9]   ; a byte field (semantic name not proven)
0x288682  cmp r1,#2
0x288684  bne.w 0x289772       ; entry to link-policy/security subpath
...
0x289772  adds r0,#0x20
0x289774  bl 0x24eedc         ; BTM_SetLinkPolicyActiveMode
0x289778  cbnz r0,0x289796
...
0x289796  ldr r2,[pc,#0x220]  ; security callback pointer
0x2897a0  ldr.w r0,[r10,#0x2c]
0x2897a4  str.w r3,[r10,#4]   ; set channel state to 2
0x2897a8  ldrh r1,[r1,#2]     ; PSM
0x2897ae  movs r2,#0          ; not originator
0x2897b4  bl 0x258e68        ; btm_sec_l2cap_access_req
0x2897b8  cmp r0,#1
0x2897bc  bne 0x2898b0
0x2897c4  bl 0x290f98        ; l2cu_send_peer_connect_rsp (pending)
```

**Proven by original ELF:** A channel/connection-record byte at `+0xC9` decides whether to branch into candidate B; the branch at `0x288684` targets `0x289772` and the subpath leads to the incoming BTM security call `0x2897b4`. The return value of the link-policy function only selects whether to skip diagnostic logging; both paths reach the security block at `0x289796` (barring exceptional termination). For the case where the byte equals 2, separate code at `0x288688` calls `0x285ec8`, which must not be conflated with the `0x2897b4` path.

**Not yet established:** The C++ field name/semantics of `connection_record+0xC9` (possibly an internal transport/security state, not necessarily an L2CAP event), the **outer CSM state/event dispatch** path that enters `0x288670`, actual DS3 run-time execution, or LMP `0x22` root cause. The `0x289694` lookup previously corrected in PR #34 is used for diagnostic logging, **not** a state/event jump. The true `0x2861ce` TBH verified in PR #35 switches on CCB state, but its event-specific predecessors to this region still require investigation.

## Next concrete reverse-engineering work

Recover the predecessor chain into block `0x288670`, including event comparison/branch conditions from the real state handler and determine the meaning of record byte `+0xC9` from writes/xrefs. Then distinguish `0x285ec8` from the BTM wrapper, and only after all branch predicates are proven label a specific `L2CEVT_L2CAP_CONNECT_REQ` path.

No binary patching, Bluetooth security exception, fake Link Key, service restart or M3 live injection. C4C-3 stays **NO-GO**.
