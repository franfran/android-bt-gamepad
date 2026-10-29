# S8 — Incoming peer connect security response branch in actual M3 ELF

Evidence: user's original `libbluetooth.so` (SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`), offline disassembly. All addresses below are ELF VMAs, not runtime addresses.

## New verified instructions at candidate B

The previously discovered incoming `l2c_csm_execute` security call `0x2897b4` is within a branch that sends a **peer L2CAP connect response** when security handling starts:

| Instruction VMA | Machine instruction | Meaning |
|---|---|---|
| `0x289798` | `movs r3,#2` | Prepare internal channel state value |
| `0x2897a4` | `str.w r3,[r10,#4]` | Set channel state (numerical value 2; symbolic name requires source mapping) |
| `0x2897a8` | `ldrh r1,[r1,#2]` | Load channel PSM from registered service record |
| `0x2897ae` | `movs r2,#0` | Non-originator security direction |
| `0x2897b4` | `bl 0x258e68` | `btm_sec_l2cap_access_req` |
| `0x2897b8` | `cmp r0,#1` | Check returned status |
| `0x2897bc` | `bne 0x2898b0` | Skip response send when status != 1 |
| `0x2897c0`/`0x2897c2` | `movs r1,#1` / `movs r2,#0` | Prepare L2CAP response args |
| `0x2897c4` | `bl 0x290f98` | **`l2cu_send_peer_connect_rsp(t_l2c_ccb*,uint16_t,uint16_t)`** |

The target `0x290f98` resolves by the **original ELF's recovered mini-debug symbol table**, not function-name guessing. The historical M3 `0x2897b4` callsite is thus explicitly coupled to pending-response handling for a peer-initiated L2CAP connection. On AOSP reference sources, `BTM_CMD_STARTED=1` results in `l2cu_send_peer_connect_rsp(p_ccb,L2CAP_CONN_PENDING,0)`; this is a useful source correspondence, but the vendor **event-selector predecessor and exact observed DS3 runtime execution** remain unproven.

## Difference from candidate A

Candidate A `0x286ea8` also passes `is_originator=0`, remote address and PSM, but continues to another state-handling block at `0x286eac` without a corresponding immediate `l2cu_send_peer_connect_rsp` call. Do not conclude that originator=0 makes the two branches equivalent. The second branch B has stronger evidence of being associated with peer-initiated L2CAP CONNECT_REQ handling.

The captured M3 HCI traffic recorded DS3 incoming HID Control PSM 0x11 followed by host Authentication Requested then authentication timeout 0x22. The present binary proof identifies a matching **security + pending response static branch**, not an observed CPU execution trace and not a proven cause of the LMP timeout.

## Offline reproduction

```sh
# Only run against exact SHA-matching original owner file:
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x289796 --stop-address=0x2897ca libbluetooth.so
readelf -Ws libbluetooth.debugdata.elf | grep 'l2cu_send_peer_connect_rsp'
```

Source correspondence (different versions may differ):
- https://android.googlesource.com/platform/system/bt/+/ea7ab70a711e642653dd5922b83aa04a53af9e0e/stack/l2cap/l2c_csm.cc
- https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/heads/main/system/stack/l2cap/l2c_csm.cc

## Gate

This proves a narrowly described **static branch** with peer response, not full jump-table/event provenance or an authorized DS3-specific workaround. No Bluetooth service changes, root injection, global security relaxation, Link Key fabrication or M3 restart. C4C-3 live gate remains **NO_GO**. Next evidence should map the jump-table predecessor to the named peer connect event and validate callback behavior without assuming completion merely from registration.
