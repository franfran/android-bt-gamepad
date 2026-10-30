# S8 — Real channel-state dispatch TBH recovered from exact M3 ARM32 ELF

Date: 2026-10-29. Original private `libbluetooth.so` SHA256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`. This is read-only **static** disassembly, not CPU execution proof.

Previous PR #34 correctly rejected the event-label indexed lookup around `0x289694` as a *diagnostic logging* table. That correction does NOT imply `l2c_csm_execute` has no real dispatch. We now identify an actual Thumb **TBH** branch:

```asm
0x2861c6  ldr r0,[r6,#4]!     ; channel state, r6=r10
0x2861ca  cmp r0,#8
0x2861cc  bhi 0x286262
0x2861ce  tbh [pc,r0,lsl #1]
0x2861d2  ; nine halfword table entries — DATA, not executable instructions
```

A Thumb TBH computes `PC + 2*table[state]` with PC at `0x2861d2`. Literal ELF file bytes decode to:

| State numeric index | Table halfword | Target ELF VMA |
|---|---|---|
| 0 | 0x0009 | 0x2861e4 |
| 1 | 0x0055 | 0x28627c |
| 2 | 0x009d | 0x28630c |
| 3 | 0x00d0 | 0x286372 |
| 4 | 0x0111 | 0x2863f4 |
| 5 | 0x0187 | 0x2864e0 |
| 6 | 0x01c7 | 0x286560 |
| 7 | 0x01ff | 0x2865d0 |
| 8 | 0x0232 | 0x286636 |

This is a **real control-flow dispatch by CCB state**, unlike the separately identified logging data table. Do not assume that a state index has the same name as in any specific AOSP revision without corroboration.

We still need to trace the event guards **inside** these state cases, especially predecessors of candidate B security call `0x2897b4` and its `l2cu_send_peer_connect_rsp` handling. Branches may jump to shared tail code outside the nine case-entry addresses. Neither the state table alone nor the historical HCI trace proves the observed DS3 request ran this candidate.

## Repeatable offline verification

```sh
python3 experiments/s8-state-tbh/verify_state_table.py /private/local/libbluetooth.so
```

The verifier requires exact original SHA, ARM32 ELF header, original `TBH` bytes and all nine actual jump-table offsets; it never loads Bluetooth processes or modifies any system. CI checks a **synthetic in-memory ELF fixture**, not the owner binary (which remains private).

**Security boundary:** unchanged global `0x36` registration, no fake link keys, no live injection. C4C-3 remains NO-GO. Exact DS3 authentication timeout `0x22` root cause remains unknown.
