# S8 — Actual M3 BTM authentication predicates and HCI 0x22 handling

**2026-10-29; private/offline ELF audit only.** Source is the owner-uploaded ARM32 `libbluetooth.so`, SHA256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`. All addresses below are original ELF VMAs (Thumb mode), not ASLR addresses. No raw binary, MAC, PIN, or Link Key is committed.

## (A) Conditions in `btm_sec_execute_procedure` immediately before Authentication Requested

The recovered M3 function begins at `0x257c04`. The previously proven direct call at `0x2580c0 → btsnd_hcic_auth_request(0x27c998)` is **conditional**. The original disassembly at `0x25802e..0x2580c4` shows:

| Original ELF instruction | Observable condition/effect |
| --- | --- |
| `0x25802e: lsls r0,r0,#0x11`; `0x258030: bmi 0x2580c6` | Earlier branch condition can **exclude** the authentication command path |
| `0x258032: ldrb r0,[r4,#0x12a]`; `0x258036: cmp r0,#0`; `0x258038: bne 0x2580c6` | Nonzero per-device field diverts away from this command path |
| `0x25803a: ldrh r0,[r4,#0x12c]`; `0x25803e: lsls r0,#0x11`; `0x258040: bpl 0x2580c6` | Another bit condition gates this path |
| `0x258042: ldrh r0,[r4,#0x10]`; `0x258044: movw r1,#0xffff`; `0x258048: cmp r0,r1`; `0x25804a: beq 0x2580c6` | ACL handle must not be `0xffff` at this point |
| `0x2580a2: ldrh r0,[r4,#0x2e]`; `0x2580a4: movw r1,#0x4010`; `0x2580a8: ands r1,r0`; `0x2580aa: cmp r1,#0x10` | Per-device security-flag check |
| `0x2580ae: ldrbeq r1,[r4,#0x12a]`; `0x2580b2: cmpeq r1,#0`; `0x2580b4: beq.w 0x258290` | Specific combined flag/state case branches to alternate handling |
| `0x2580b8: ldrh r0,[r4,#0x10]`; `0x2580bc: strb r5,[r4,#0x129]` (r5=1) | Pass ACL handle in r0 and set authentication-procedure state byte `+0x129` to 1 |
| `0x2580c0: bl 0x27c998` | Send HCI **Authentication Requested** through `btsnd_hcic_auth_request`, builder opcode **0x0411** (PR #39) |

**Interpretation boundary:** These are proven machine-code predicates/effects, **not** a fully decoded vendor `tBTM_SEC_DEV_REC` struct layout. Do not claim a particular state/bit name or that the observed DS3 runtime necessarily entered this exact branch. A static host call is consistent with historical btsnoop #151 (`0x0411`) but does not identify the firmware-level failure.

## (B) `btm_sec_auth_complete` on status 0x22

The recovered function starts at `0x25b5c4`. HCI status comes as second argument `r1` and is saved to `[sp,#0xaf]` at `0x25b5e6`. Actual control-flow from the private ELF:

1. `0x25b786: ldrb r6,[sp,#0xaf]`, `0x25b78a: cmp r6,#0x2a`, `0x25b78e: cmpne r6,#0x23`, `0x25b790: bne 0x25b7ac`. **HCI `0x22`** is neither special code `0x2a` nor `0x23`; it enters the general branch at `0x25b7ac`. These special cases must not be mistaken for `0x22`.
2. `0x25b7ac` looks up the device's security record. If present, it clears bit `0x02` of record byte `+0x130` at `0x25b7ba..0x25b7be` and follows additional conditional cleanup. This bit's precise vendor name is not independently established.
3. `0x25b7de..0x25b80c` clears several outstanding security-related fields, with conditional command calls. The labels/types of all global offsets need further corroboration.
4. `0x25b836: ldrb r0,[r10,#0x129]`; `0x25b83a: cmp r0,#1`; when equal it enters completion handling, and `0x25b844: strb r5,[r10,#0x129]` (r5=0) resets the in-progress auth state.
5. `0x25b848: cmp r0,#0`; status zero takes success branch `0x25b8dc`. For the historical nonzero status **0x22**, it does **not** take success. `0x25b84c: cmp r0,#0x0c` handles another special error, and `0x22` instead reaches `0x25b8ea` via `0x25b84e: bne`.
6. `0x25b914..0x25b934` includes a **guarded indirect callback** via `blx r7` at `0x25b934`, using the remote security-record fields as arguments. Its actual invocation depends on the preceding conditions; **this does not prove a Java bond rollback or any particular L2CAP callback ran for DS3**.

**Observed vs derived:** Historical btsnoop recorded HCI Authentication Complete status `0x22`, Disconnection Complete reason `0x22`, and Java bond rollback to `BOND_NONE`. The native code shows an available general failure handling path and auth-in-progress reset. It **does not by itself prove** the specific Java notification origin, which callback ran or whether DS3/M3 controller firmware was responsible for LMP timeout.

## Engineering conclusion

We now have static original-device evidence for (i) incoming L2CAP peer connection / Classic security path (PR #38), (ii) conditional BTM HCI authentication request builder (PR #39), and (iii) native failure-status handling with distinct `0x22` semantics (this report). However **no patch is justified from this evidence**: changing the `0x36` global HID security mask or skipping HCI auth for a MAC-like identity would weaken security and may still fail to produce valid HID channels. A viable DS3-only approach needs trusted cable enrollment, protocol compatibility proof and independent recovery/rollback validation.

**Recommended next research:** identify and model the guarded auth-completion callback at `0x25b934` and capture exact L2CAP channel-security result transitions in an offline source-level harness. Separately assess DS3 firmware/BR-EDR interoperability using owner-authorized passive evidence before deciding if an M3 userspace policy exception can help. Continue treating the live S7 C4C-3 gate as **NO_GO**.

## Reproduce (read-only, exact matching original ELF)

```sh
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x25802e --stop-address=0x2580c6 libbluetooth.so
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x25b786 --stop-address=0x25b936 libbluetooth.so
```
