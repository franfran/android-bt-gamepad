# S8 — M3 incoming L2CAP security candidates: actual PSM argument provenance

2026-10-29. Offline inspection of operator-supplied exact M3 ARM32 `libbluetooth.so`, SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`. No vendor binary committed or modified. Addresses are ELF VMAs, not live process addresses.

## New machine-code finding

Draft PR #31 established `l2c_csm_execute` has two `is_originator=false` candidate calls to `btm_sec_l2cap_access_req`. This inspection follows the **PSM argument** (`r1`, per AAPCS) backward from each call:

| Item | Incoming candidate A | Incoming candidate B |
|---|---|---|
| Security BL | `0x286ea8 → 0x258e68` | `0x2897b4 → 0x258e68` |
| PSM service-record pointer | `0x286e92: ldr.w r1,[r10,#0x38]` | `0x28979a: ldr.w r1,[r10,#0x38]` |
| PSM retrieval | `0x286e9c: ldrh r1,[r1,#0x2]` | `0x2897a8: ldrh r1,[r1,#0x2]` |
| Remote address pointer | `0x286e98: ldr.w r0,[r10,#0x2c]`; `0x286e9e: adds r0,#0x20` | `0x2897a0: ldr.w r0,[r10,#0x2c]`; `0x2897aa: adds r0,#0x20` |
| Callback | `0x286ea0: ldr r3,[r2]` | `0x2897ac: ldr r3,[r2]` |
| Direction | `0x286ea2: movs r2,#0` | `0x2897ae: movs r2,#0` |
| User-data callback context | `0x286ea4: str.w r10,[sp]` | `0x2897b0: str.w r10,[sp]` |

**Proven:** Both incoming candidates pass PSM dynamically from the channel's `r10+0x38` service-record pointer, then 16-bit field `+0x02`, and pass a remote address pointer from `r10+0x2c` + `0x20`. They do not hardcode PSM 0x11 at the security call itself. This is the first verified link between the channel service record and the BTM security-call PSM argument. It strengthens the per-channel direction/identity-context evidence substantially.

## Different predecessor and successor control flow

Candidate A is entered at `0x286e90` and preceded in the same basic-block neighborhood by branches out of other event handling (e.g. `0x286e80 → 0x286eac` and `0x286e8e → 0x286eac`). After its security call, execution continues at `0x286eac`, where additional state handling begins. Candidate B begins at `0x289796`, follows a previous state/function segment, **stores a channel state value** at `0x2897a4: str.w r3,[r10,#0x4]` with `r3=2`, then calls BTM security. At `0x2897b8` it compares return `r0` to `1`; if not equal it branches to `0x2898b0`; otherwise it calls another channel routine at `0x2897c4`. Therefore B immediately performs a status-sensitive security result transition while A follows different downstream code.

This is **static branch-local evidence**, not a reconstructed complete jump table or proof that a given DS3 event reached B. Large regions near `0x2896a4` are **inline data / relative dispatch table**, and a naive linear Thumb disassembler prints nonsensical instructions there. Never interpret those bytes as executable security logic. Resolve true predecessor event dispatch using data xrefs / switch-table targets before claiming exact state/event selection.

## Integration significance

Earlier real capture: incoming DS3 HID Control PSM 0x11 L2CAP request → host HCI Authentication Requested → link-key negative → PIN flow → HCI 0x22. This report establishes that both likely incoming security paths carry channel PSM and device context to the BTM wrapper. **It still does not demonstrate that either PSM equals 0x11 at runtime**, identify which callsite executes, or establish why controller authentication times out.

No patch, no relaxation of global HID security mask `0x36`, no key fabrication, no device operations. S7 C4C-3 live injection remains **NO-GO**.

## Reproduction

Using exact original binary:

```sh
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x286e90 --stop-address=0x286eb0 libbluetooth.so
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x289796 --stop-address=0x2897c8 libbluetooth.so
```

Next meaningful work: find actual `l2c_csm_execute` event jump-table branches entering `0x286e90` and `0x289796` and inspect their channel state and event. A source comparison with Android 12 can constrain hypotheses but not prove vendor runtime execution.
