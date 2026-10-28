# RetroBox / iMETBOX M3 — Stage 3C Gate 2: HID security decision trace

**Scope:** Offline, read-only analysis of the user's actual Android 12 ARM32 `libbluetooth.so` and its embedded mini-debug ELF. No device binaries were modified. This report is not a deployable patch.

## Newly confirmed result: 0x36 is symmetric authentication + encryption

The M3's `hidh_conn_reg()` places `0x36` in the security-level argument for BOTH `L2CA_Register2` calls (HID Control `0x11` and Interrupt `0x13`). The contemporary AOSP BTM definitions assign:

| Constant | Value | Semantics |
|---|---:|---|
| `BTM_SEC_IN_AUTHENTICATE` | `0x02` | Authenticate incoming channel |
| `BTM_SEC_IN_ENCRYPT` | `0x04` | Encrypt incoming channel |
| `BTM_SEC_OUT_AUTHENTICATE` | `0x10` | Authenticate outgoing channel |
| `BTM_SEC_OUT_ENCRYPT` | `0x20` | Encrypt outgoing channel |
| **OR of all four** | **`0x36`** | **Authentication + encryption in both directions** |

That is consistent with `BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT`. This establishes the intended service policy, **not** a safe patch. Changing the registration mask would affect ALL controllers connecting to the HID PSMs.

References:
- https://android.googlesource.com/platform/system/bt/+/911d1ae03efec2d54c3b1b605589d790d1745488/stack/include/btm_api_types.h
- https://android.googlesource.com/platform/system/bt/+/f394aeca52bbecba6bd9c55e449306749fe2c1c7/bta/include/bta_api.h

## Verified M3 machine-code callsites (Thumb-2, ELF virtual addresses)

| Caller | Callsite | Callee | Evidence |
|---|---|---|---|
| `hidh_conn_reg` | `0x27e79c` | `L2CA_Register2`, `0x281368` | Control PSM `0x11`, security argument `0x36` |
| `hidh_conn_reg` | `0x27e7b2` | `L2CA_Register2`, `0x281368` | Interrupt PSM `0x13`, same security argument |
| `L2CA_Register2` | `0x281394` | `BTM_SetSecurityLevel`, `0x256608` | Registers service security policy |
| `btm_sec_l2cap_access_req` | `0x258ffe` | `btm_sec_l2cap_access_req_by_requirement`, `0x258734` | Passes L2CAP requirement into per-remote security handling |
| `btm_sec_l2cap_access_req_by_requirement` | `0x258b5a` | `btm_sec_execute_procedure`, `0x257c04` | Triggers security procedure on an eligible branch |
| `btm_sec_mx_access_request` | `0x2590d2` | `bluetooth::shim::is_gd_shim_enabled`, `0x2eff7e` | Runtime choice exists |
| `btm_sec_mx_access_request` | `0x2590e2` | GD shim variant, `0x2cf5c2` | Alternative route exists |
| `btm_sec_mx_access_request` | `0x2592dc` | `btm_sec_execute_procedure` | Legacy branch exists |

The callsite at `0x258ffe` and `0x258b5a` is verified by disassembling the actual uploaded binary; the rest are independently reconfirmed or carried forward from the prior validated inventory. Note that the exact dynamic dispatch from the HID L2CAP callback to the legacy or GD security path has **not** yet been demonstrated. The `btm_sec_l2cap_access_req` wrapper takes remote `RawAddress`, PSM, `is_originator`, and callback; the `by_requirement` function also has the remote address and calculated security mask. The latter is a **candidate for a narrowly scoped policy hook**, subject to proving the actual runtime path and trusted enrollment mechanism.

## What the HCI log proves versus what it doesn't

The recorded DS3 incoming HID Control L2CAP attempt precedes host authentication request, link-key lookup, PIN request/reply and timeout `0x22`. This is compatible with HID service security initiating authentication. It does **not** prove which exact machine-code branch executed, or guarantee a successful HID connection if authentication is suppressed. The Java `HidHostService` bond check may block non-bonded input later.

## Recommended next safe experiment

**Do not change `0x36` globally, forge Link Keys, or replace the original `/system/lib/libbluetooth.so`.** Stage 3C's next gate should be a **runtime path observation**, preferably via supported Android Bluetooth debugging/logging or a reversible userspace instrumentation method; verify whether `btm_sec_l2cap_access_req_by_requirement` or GD-specific handlers execute during the DS3 connection. After that, implement an enrolled-MAC + explicit USB-verified authorization guard within the *per-device* service-security decision, followed by a separate HID authorization test. Identify a boot-safe, removable overlay or alternate-process test before any live code injection.

**Status:** Service flag semantics and two key security callsites confirmed. Complete end-to-end runtime path and safe exception implementation **not yet proven**.

## Reproduce offline

```sh
readelf -Ws libbluetooth.debugdata.elf | grep -E 'btm_sec_l2cap_access_req|btm_sec_execute_procedure|hidh_conn_reg|L2CA_Register2'
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x27e748 --stop-address=0x27e7b8 libbluetooth.so
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x258e68 --stop-address=0x259060 libbluetooth.so
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x258734 --stop-address=0x258d50 libbluetooth.so
```
