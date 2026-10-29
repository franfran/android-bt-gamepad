# S8 native security callgraph contract — offline only

This milestone directly builds on the **already known** M3 DS3 failure: incoming HID Control PSM 0x11, HCI Authentication Requested, Link Key negative, PIN reply, Authentication Complete **0x22**, then disconnect. It does not repeat device discovery or claim that a global Bluetooth auth bypass would fix the controller.

Source-of-truth static evidence: `research/retrobox-stage3c-callgraph.txt`, generated from the actual M3 `libbluetooth.so` and recovered `.gnu_debugdata` symbol table. Run from repository root:

```sh
python3 experiments/s8-security-contract/callgraph_contract.py research/retrobox-stage3c-callgraph.txt
```

Checks the specific recovered function ranges and six identified direct call edges; fails closed on missing or altered evidence. Tests use the actual committed callgraph text, not invented M3 process output. **No M3 access, code injection, service action, or binary patch.**

## Confirmed direct edges in saved offline disassembly

- `hidh_conn_reg` at `0x27e748`: `0x27e79c` and `0x27e7b2` call `L2CA_Register2` at `0x281368`. Previous binary audit found same `0x36` security mask for PSM 0x11 and 0x13; **global** registration must never be weakened.
- `btm_sec_mx_access_request` at `0x2590a8`: `0x2590d2` calls `is_gd_shim_enabled`, `0x2590e2` calls shim access request and `0x2592dc` calls legacy `btm_sec_execute_procedure`. Existence of both branches is *not* runtime branch selection.
- `btm_sec_l2cap_access_req_by_requirement` at `0x258734`: `0x258b5a` calls `btm_sec_execute_procedure`.
- `hidh_l2cif_connect_ind` at `0x27ee28`: direct calls include `HID_HostAddDev` and `L2CA_DisconnectReq`, **but** several BLX targets are unresolved. The archived callgraph does *not* prove the exact callback -> native security request -> HCI Authentication Requested sequence.

These offsets are historical ELF VMAs, never reusable live addresses or patch instructions.

## Security/context conclusion

The Android 12 reference `btm_sec_l2cap_access_req` wrapper takes PSM, but `btm_sec_l2cap_access_req_by_requirement` does not carry an independent PSM argument. Any future DS3-specific decision must have reliable **source/device/HID context at the actual selected callsite**; matching a remote address alone, or globally altering `0x36`, is unsafe. The existing `experiments/stage3c-policy/` candidate-only model remains an unintegrated test, not authorization to weaken link security.

## Next *material* engineering evidence

Resolve exact `hidh_l2cif_connect_ind` callback registration and indirect BLX dispatch using archived M3 ELF/mini-debug **only if locally retained**. Prefer branch-target disassembly, callback struct xrefs and function signature/argument propagation. If the original binary isn't available, label the missing edge UNVERIFIED rather than drawing it from AOSP alone. Then create a standalone source-level emulation exercising the candidate scoped DS3 decision *without altering or bypassing Bluetooth authentication*. Existing C4C-3 NO-GO and independent recovery gate apply to any later live M3 work.
