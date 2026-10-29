# S8 — Correct event provenance: diagnostic table is not CSM dispatch

**Input:** exact owner-uploaded M3 `libbluetooth.so` (SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`), analyzed offline. This report deliberately distinguishes instruction-level proof from proposed event naming.

## Correction to the previous research direction

The PC-relative indexed load at `0x289694..0x2896a0` was initially a candidate for an event dispatch table. **It is not evidence of a control-flow jump table:**

```asm
0x28968e  cmp.w r8,#0x2d
0x289692  bhi 0x289728
0x289694  ldr r1,[pc,#0x348]     ; literal at 0x2899e0
0x289696  sxth.w r2,r8
0x28969a  add r1,pc
0x28969c  ldr.w r4,[r1,r2,lsl #2]
0x2896a0  b 0x28972c
...
0x289746  strd r4,r8,[sp,#16]
0x28974c  bl 0x5dd460           ; __android_log_print
```

The value selected by event index `r8` is **used as data in a logging call**, not loaded into PC or branched to. It is therefore an event-label/diagnostic lookup candidate, **not a proven event-to-basic-block dispatch table**. Linear disassembly of inline bytes `0x2896a4..0x289728` produces nonsensical Thumb instructions; do not treat them as runnable code or silently infer a switch from those bytes.

## New concrete incoming candidate B predecessor

```asm
0x289772  adds r0,#0x20
0x289774  bl 0x24eedc
0x289778  cbnz r0,0x289796
0x28977a..0x289792  diagnostic log setup and __android_log_print
0x289796  ldr r2,[pc,#0x220]     ; callback reference
0x289798  movs r3,#2
...
0x2897b4  bl 0x258e68           ; btm_sec_l2cap_access_req
0x2897b8  cmp r0,#1
0x2897bc  bne 0x2898b0
0x2897c0  movs r1,#1
0x2897c2  movs r2,#0
0x2897c4  bl 0x290f98           ; l2cu_send_peer_connect_rsp
```

**Proven**: The immediate predecessor at `0x289778` conditionally jumps into `0x289796` based on `r0` from `0x24eedc`, and the fall-through path logs then reaches the same block. Candidate B submits incoming security requirements then sends a peer connection response only when BTM returns 1. This further explains the *local* branch, but neither the `0x24eedc` function's return semantics nor the outer CSM event selector are established here.

**NOT proven**: the precise `L2CEVT_L2CAP_CONNECT_REQ` enum value, event dispatch target into this subgraph, actual CPU execution in DS3 capture, or cause of HCI `0x22`. Do **not** label this path as a verified event-to-callsite mapping based on AOSP alone.

## Next genuine reverse-engineering target

Find the enclosing `l2c_csm_execute` entry's real control-flow selection for event and channel state. Specifically: independently identify actual conditional branches or jump-table entries whose **loaded value is used as an instruction target**, then show a direct path to `0x289772` / `0x289796` and the PSM-bearing CCB. Read-only static analysis only. The shared HID `0x36` authentication requirement must not be globally relaxed. C4C-3 live injection **NO-GO** remains.
