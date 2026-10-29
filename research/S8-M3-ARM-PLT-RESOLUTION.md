# S8 actual M3 ELF: BLX target resolution (2026-10-29)

## Provenance and validation

Operator provided the original M3 `libbluetooth.so` as a ZIP in ChatGPT; analyzed **locally only**, never stored in this repository. Exact unpacked SHA-256: `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`; ARM32 EABI5, Android 31, GNU Build ID `0d29a62178e43066e018216c1f1d5b18`. Both IDs match historical Stage 3C records.

Read-only ELF section/relocation inspection found `.plt` at ELF VMA `0x5dee30` and `.rel.plt` with `R_ARM_JUMP_SLOT` entries. PLT call entries begin `0x5dee50` and are 16 bytes apart; map entry N to the Nth relocation. Crucially these are **ARM-state PLT stubs** reached by Thumb `blx`; `--triple=thumbv7-linux-androideabi` erroneously decodes their ARM bytes as nonsensical Thumb. Use automatic ELF architecture ARM decoding for the target windows, not forced Thumb.

## Resolved imported symbols

| Thumb BLX destination (ELF VMA) | ARM PLT relocation target |
|---|---|
| `0x5dee60` | `__stack_chk_fail@LIBC` |
| `0x5deea0` | `_Znwj` (C++ operator new) |
| `0x5df050` | `base::StringPrintf(char const*, ...)` |
| `0x5dee90` | `_ZdlPv` (C++ operator delete) |
| `0x5dee70` | `abort@LIBC` |
| `0x5df090` | `std::string::replace(...)` |

Method: identify the actual PLT stub VMA in `llvm-objdump -d --start-address=... --stop-address=...`, map entry index `(address - 0x5dee50) / 16` to the same-index `R_ARM_JUMP_SLOT` in `readelf -rW`, and verify ARM stub `add r12, pc; add r12; ldr pc, [r12,...]!`. These mappings are specific to the verified M3 ELF, **not** live ASLR addresses or patches.

### Consequence

These particular previously unresolved `blx` calls in `hidh_l2cif_connect_ind` are imported support functions, **not directly Bluetooth security-management hooks**. The archived callgraph's name resolution had failed because the mini-debug table did not resolve PLT imports. This resolves the relevant **immediate branch destinations**, but **does not** establish how HID registration callbacks invoke `btm_sec_l2cap_access_req` or `btm_sec_mx_access_request`.

## Next useful work

Trace the **actual `tL2CAP_APPL_INFO` callback table** passed via register r1 in `hidh_conn_reg` for both PSMs, and the L2CAP layer's registration/security dispatch. `hidh_conn_reg` loads PSM `0x11` then `0x13`, passes `sec_level=0x36` as seventh argument. The callback table is populated elsewhere and must be confirmed by binary xrefs; following ordinary PLT helper symbols is a dead end.

This result **does not** authorize DS3 auth bypass, global `0x36` modification, replacing firmware, live injection or restarting Bluetooth. Existing C4C-3 NO-GO persists.
