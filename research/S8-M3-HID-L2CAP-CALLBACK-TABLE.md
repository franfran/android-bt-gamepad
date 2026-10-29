# S8 — Actual M3 HID L2CAP callback table recovered (offline)

**Evidence:** Owner-uploaded original M3 `libbluetooth.so` in the current analysis session, inspected locally and **not committed**. SHA256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`; Build ID `0d29a62178e43066e018216c1f1d5b18`. Exact same original Stage 3C vendor image.

## Direct binary proof

At ARM32 Thumb `hidh_conn_reg()` ELF VMA `0x27e748`, both registrations call `L2CA_Register2` at `0x281368` with PSM 0x11 and 0x13 respectively, **sharing the same `r1` application callback table pointer**:

| PSM registration | Literal loaded | PC-relative add | Computed callback-table VMA |
|---|---|---|---|
| HID Control, `0x27e79c` | `ldr r1, [pc,#0xcc]` at `0x27e752` → `[0x27e820] = 0x00366970` | `add r1,pc` at `0x27e75c`, Thumb PC `0x27e760` | **`0x5e50d0`** |
| HID Interrupt, `0x27e7b2` | `ldr r1,[pc,#0x84]` at `0x27e7a2` → `[0x27e828] = 0x00366922` | `add r1,pc` at `0x27e7aa`, Thumb PC `0x27e7ae` | **`0x5e50d0`** |

The callback table is within the ELF **RW PT_LOAD** segment with `p_vaddr=0x5e2090` and `p_offset=0x5e0090`; read file bytes via actual program headers, NOT using a single file-offset==VMA assumption.

| Callback-table entry offset | ELF value | Recovered symbol |
|---|---|---|
| `+0x00` | `0x27ee29` | **`hidh_l2cif_connect_ind`**, Thumb pointer |
| `+0x04` | `0x27f0f9` | `hidh_l2cif_connect_cfm`, Thumb pointer |
| `+0x08` | `0x27f2ad` | HID callback (symbol resolution still pending) |
| `+0x0c` | `0x27f331` | HID callback (symbol resolution still pending) |
| `+0x10` | `0x27f6a5` | HID callback (symbol resolution still pending) |
| `+0x14` | `0x27f8c5` | HID callback (symbol resolution still pending) |
| `+0x18` | `0x27fa21` | HID callback (symbol resolution still pending) |
| `+0x1c` | `NULL` | no callback |
| `+0x20` | `0x27fa99` | HID callback (symbol resolution still pending) |

**Conclusion:** We have **proved static registration** of the actual M3 HID incoming L2CAP callback, not merely guessed it from AOSP or assumed PLT helper calls were a native security callback. This is a significant previously missing edge. The table includes Thumb-bit pointers and is registered on both HID PSMs with the original `0x36` security setting.

**Important limit:** This does not prove the callback ran in the previously captured DS3 wireless attempt, or reveal the runtime bridge from L2CAP security registration to `btm_sec_l2cap_access_req` / `btm_sec_mx_access_request`. Connection code may perform authentication **inside L2CAP before invoking the HID callback**. Do not infer the callback is the function directly issuing `HCI Authentication Requested`. Follow the L2CAP service-security flow, especially `L2CA_Register2` and `BTM_SetSecurityLevel`, with source-control and per-device identity preserved.

## Reproducibility

```sh
python3 experiments/s8-hid-callback/verify_callback_table.py /private/local/path/libbluetooth.so
```

Exact ELF SHA is required, and the script verifies ELF32 ARM, both Thumb literal references, both computed identical table addresses and callback entries. Host CI uses a **synthetic** ELF-like test fixture to avoid publishing the owner's vendor binary. The actual input was checked in the private analysis environment. No M3 action or mutation, process loading, Bluetooth restart, global security relaxation or firmware patch.

**Status:** STATIC_CALLBACK_REGISTRATION_VERIFIED; runtime callback dispatch / DS3-only authorization / HCI 0x22 cause UNVERIFIED; live Bluetooth injection **NO-GO**.
