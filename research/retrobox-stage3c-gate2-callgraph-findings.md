# RetroBox M3 — Stage 3C Gate 2: verified Thumb-2 callsites

Date: 2026-10-25. Inputs: user-extracted M3 `libbluetooth.so` and its `.gnu_debugdata` mini-debug ELF. **Offline investigation only; no patch and no device changes.**

## Concrete new evidence

Reconstructed **direct Thumb-2 branch/call targets** using `llvm-objdump` and named them by independently recovered ELF function ranges. Included a standalone `retrobox-stage3c-callgraph.py` tool and sample output.

### 1. HID registration, verified

`hidh_conn_reg()` begins at virtual address `0x27e748` (232-byte function). At:

- `0x27e796`: `movs r0, #0x11`
- `0x27e79c`: `bl 0x281368` → `L2CA_Register2(...)`
- `0x27e7a4`: `movs r0, #0x13`
- `0x27e7b2`: `bl 0x281368` → `L2CA_Register2(...)`

The function passes a common registration parameters structure, including an immediate `0x36` loaded at `0x27e75e` and later placed on the stack. **Do not interpret the numeric flags as confirmed authentication-policy semantics until the callee's parameter layout and ABI are established.**

### 2. HID incoming callback, verified

`hidh_l2cif_connect_ind(...)` begins `0x27ee28` (720 bytes). Direct callsites include:

- `0x27ee74` → `HID_HostAddDev(...)` (`0x27e3c8`)
- `0x27ee7c` → `L2CA_DisconnectReq(...)` (`0x282b18`)
- `0x27eef8` → `hid_conn::state_text(...)` (`0x27fc08`)
- `0x27ef2e`, `0x27f046` → `BTM_LogHistory(...)` (`0x24d5b0`)

There are several unresolved indirect/veneer calls such as `0x27ef1e: blx 0x5df050`. These callsites **are not proof of which precise security routine is called**. The function does compare incoming PSM against `0x11` and `0x13`, but interpreting its higher-level behavior requires callback and thunk resolution.

### 3. Security manager, verified

`btm_sec_mx_access_request(...)` at `0x2590a8` (1904 bytes) contains:

- `0x2590d2` → `bluetooth::shim::is_gd_shim_enabled()` (`0x2eff7e`)
- `0x2590e2` → `bluetooth::shim::btm_sec_mx_access_request(...)` (`0x2cf5c2`)
- `0x2590ee` → `btm_find_or_alloc_dev(...)` (`0x24a41c`)
- `0x2592dc` → `btm_sec_execute_procedure(...)` (`0x257c04`)

This demonstrates both **legacy and GD shim** code paths within the binary. Which route M3 uses at runtime was **not** established. The direct call into `btm_sec_execute_procedure()` is verified; the broader HID-callback → security-manager linkage is not yet fully reconstructed.

## Implications

- HCI capture previously established HID Control PSM `0x11` incoming before HCI Authentication Requested → Link Key Request/Negative Reply → PIN Code Request/Reply → timeout `0x22`.
- Current disassembly independently confirms the HID host registers `0x11` and `0x13`, and confirms security manager has machinery to perform security procedures.
- **Not proven:** exact dynamic call chain from the incoming HID callback to the HCI Authentication Requested command; runtime path through `shim`; feasibility of a device-specific exception; whether downstream `HidHostService.okToConnect()` will reject a non-bonded DS3 after transport succeeds.

## Next safe engineering gate

1. Resolve linkage and indirect branch stubs around `hidh_l2cif_connect_ind()` and the L2CAP registration callback table; map the security flags **in the registration callee**.
2. Identify whether this M3 binary uses GD shim or legacy security flow at runtime with non-invasive instrumentation/logging.
3. Design a DS3-only exception based on explicit USB authorization, not MAC/name alone. Do not globally disable authentication or manually fabricate Link Keys.
4. Demonstrate a reversible way to load modified stack code in a test environment before considering any system partition changes; require verified recovery and independent access via ADB.

No deployable patch is claimed by this report.

## Reproduction

```sh
python3 retrobox-stage3c-callgraph.py \
  libbluetooth.so libbluetooth.debugdata.elf \
  > retrobox-stage3c-callgraph.txt
```

Mini-debug ELF extraction and its originating offsets were documented in `retrobox-stage3c-gate2-native-symbol-recovery.md`. Addresses here are **ELF virtual addresses**, not file offsets.
