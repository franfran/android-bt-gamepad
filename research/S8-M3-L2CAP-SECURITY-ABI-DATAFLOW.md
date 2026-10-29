# S8 — M3 L2CAP registration propagates HID security mask to BTM (offline original ELF)

**Input**: owner-uploaded original M3 ARM32 `libbluetooth.so`, SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`, GNU Build ID `0d29a62178e43066e018216c1f1d5b18`. Original ELF analyzed offline, never added to repository. Static addresses below are **ELF virtual addresses**, not live addresses or patch locations.

## Newly validated argument flow

This continuation moves **one real step beyond** the callback table recovered in Draft PR #28. Thumb disassembly of the exact M3 binary establishes the following source → destination flow:

1. `hidh_conn_reg()` at `0x27e748`: instruction `0x27e75e: movs r7,#0x36`. At `0x27e76e: str r7,[sp,#0x8]` the `0x36` value is positioned as the **seventh AAPCS argument** to `L2CA_Register2`. The first HID registration calls `L2CA_Register2` at `0x27e79c` with `r0=0x11`, and the second at `0x27e7b2` with `r0=0x13` and the same stacked argument.
2. `L2CA_Register2` at `0x281368` begins `push {r4,r5,r6,lr}; sub sp,#0x10`. At `0x281372: ldr r5,[sp,#0x28]` it recovers the **seventh incoming argument**, accounting for the 16-byte register-save push plus 16-byte local stack allocation. This is the same `0x36` passed by the HID caller.
3. At `0x281392: mov r3,r5`, then `0x281394: bl 0x256608` the wrapper passes that value into `BTM_SetSecurityLevel` as the **fourth argument**, with `r0=0`, `r1` a local string pointer, and `r2=0`. The fifth argument at `[sp]` carries the requested PSM via `r4`. This is the actual M3 machine-code link from HID's `0x36` requirement to BTM service-security registration.

### Evidence table (actual Thumb instructions)

| ELF VMA | Instruction | Static meaning |
| --- | --- | --- |
| `0x27e75e` | `movs r7,#0x36` | HID security requirement constant |
| `0x27e76e` | `str r7,[sp,#0x8]` | 7th argument to L2CA_Register2 |
| `0x27e796` / `0x27e79c` | `movs r0,#0x11`; `bl 0x281368` | HID Control registers |
| `0x27e7a4` / `0x27e7b2` | `movs r0,#0x13`; `bl 0x281368` | HID Interrupt registers |
| `0x281372` | `ldr r5,[sp,#0x28]` | L2CA retrieves incoming 7th argument |
| `0x281392` / `0x281394` | `mov r3,r5`; `bl 0x256608` | BTM_SetSecurityLevel receives it |

**Meaning:** `0x36` is not an accidentally similar constant or a guessed AOSP default: the M3 binary explicitly routes it to `BTM_SetSecurityLevel` for both HID PSMs. The prior Stage 3C header review interprets it as incoming and outgoing authentication/encryption requirements. The fourth-argument identification depends on AAPCS argument rules and is directly supported by the instruction flow.

## What is NOT proved

This static proof establishes **service registration**, not which security decision actually executes for the incoming DS3 connection. The previously recorded HCI sequence proves an incoming HID Control request occurred before HCI Authentication Requested, then timeout `0x22`; registration alone does not establish which runtime branch triggered that command. We also do **not** yet know whether bypassing authentication would allow useful traffic or create unsafe unauthenticated HID; do not attempt such a bypass.

The next engineering task is to trace the *service registry lookup* in L2CAP incoming connection handling and the actual call into `btm_sec_l2cap_access_req` or `btm_sec_mx_access_request`, preserving both remote identity and PSM. A separate original-ELF disassembly of `L2CA_Register2` and `BTM_SetSecurityLevel` can guide this, but **do not infer runtime state from static code alone**.

## Reproduce privately

```bash
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x27e748 --stop-address=0x27e7b8 /private/local/libbluetooth.so
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x281368 --stop-address=0x28139e /private/local/libbluetooth.so
```

Review the specific instructions above against the SHA-verified original M3 file. No system installation, device restart, code injection, global security reduction, raw HCI data publication or firmware modification. The live C4C-3 recovery/namespace **NO-GO** remains in force.
