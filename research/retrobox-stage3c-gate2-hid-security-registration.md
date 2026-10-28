# RetroBox / M3 — Stage 3C Gate 2: Verified HID security registration

## Materials

Device-provided ARM32 Android 12 `/system/lib/libbluetooth.so`, saved as `/mnt/data/m3-native-work/libbluetooth.so`; embedded `.gnu_debugdata` symbol table extracted to `libbluetooth.debugdata.elf`. Analysis is read-only offline. No deployed patch was built.

## Findings reproduced from M3 binary

- `hidh_conn_reg()` starts at Thumb code address `0x27e748` (ELF symbol encodes Thumb as `0x27e749`). It registers HID Control PSM `0x11` and HID Interrupt PSM `0x13`.
- At `0x27e758`, `mov.w r6, #0x280` sets the L2CAP MTU argument. At `0x27e75e`, `movs r7, #0x36` sets the value passed as seventh argument (`sec_level`) to **both** calls to `L2CA_Register2()`.
- Control PSM: `movs r0, #0x11` at `0x27e796`, followed by `bl L2CA_Register2` at `0x27e79c`.
- Interrupt PSM: `movs r0, #0x13` at `0x27e7a4`, followed by `bl L2CA_Register2` at `0x27e7b2`.
- `L2CA_Register2` address `0x281368`, internally calls `BTM_SetSecurityLevel` at `0x281394` (target `0x256608`). Android AOSP's matching API takes `sec_level` as its seventh argument and registers it via `BTM_SetSecurityLevel(false, "", 0, sec_level, psm, 0, 0)`.
- Thus **M3 unconditionally registers BOTH HID channels with security mask 0x36 at service-registration time**. This registration is not DS3-specific and applies to all Bluetooth HID hosts.
- `btm_sec_mx_access_request` calls `bluetooth::shim::is_gd_shim_enabled()` at `0x2590d2`; the latter branches into `bluetooth::common::init_flags::gd_core_is_enabled` at `0x2eff7e`. This proves a runtime flag exists in the binary, NOT which path is active on M3.

## Source correspondence

- Android AOSP HID host `hidh_conn_reg` registers both PSMs with `BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT` (as observed in Android platform source).
- AOSP `L2CA_Register2` passes the requested security level to `BTM_SetSecurityLevel`.

## Consequences and caution

The HCI snoop showed DS3's incoming HID Control request before `Authentication Requested`, followed by `Link Key Request`, `PIN Code Request`, and `0x22` timeout. The registration flags are a concrete candidate for **why** authentication is required, but this trace alone does not prove the precise M3 branch which sent the HCI command. The mask `0x36` should be explained in terms of build-specific bit definitions; do not claim all sub-bits from the integer alone without matching headers.

**Do not patch a hard-coded `0x36` to zero.** Since `hidh_conn_reg()` globally registers both HID PSMs, that would reduce security for all Bluetooth HID devices, not just DS3. Any viable DS3 exception must apply per-remote-device, after verifying an explicit local trust enrollment such as USB cable pairing, and may require changes to both native security handling and Android HID Host bonded-state authorization. An unknown MAC is not sufficient proof of trust. Never fabricate a Link Key.

## Next gate

1. Inspect security bitfield definitions in matching platform source and describe 0x36 precisely.
2. Trace `BTM_SetSecurityLevel -> L2CAP incoming security lookup -> btm_sec_mx_access_request / btm_sec_execute_procedure` and identify a per-device policy hook.
3. Establish which GD/legacy runtime path is active **without editing system files**.
4. Design a reversible instrumented test (not a global security bypass), with backup/rollback and a separate trusted-controller enrollment.

## Reproducible commands

```sh
readelf -Ws libbluetooth.debugdata.elf | grep -E 'hidh_conn_reg|L2CA_Register2|BTM_SetSecurityLevel'
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x27e748 --stop-address=0x27e819 libbluetooth.so
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x281368 --stop-address=0x28139e libbluetooth.so
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x2eff7e --stop-address=0x2eff82 libbluetooth.so
```
