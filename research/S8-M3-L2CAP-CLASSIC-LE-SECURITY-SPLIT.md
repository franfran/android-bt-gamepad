# S8 — M3 incoming L2CAP path splits LE vs Classic security

**Date:** 2026-10-29. **Evidence:** Owner-uploaded original M3 ARM32 `libbluetooth.so`, unpacked SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`. Read-only local analysis; ELF never committed. Function names recovered from **this exact ELF's** XZ-compressed `.gnu_debugdata` mini-debug symbol table, not guessed from AOSP. Addresses are original ELF VMAs, not live patch locations.

## Important resolution of PR #36's unknown field / branch

```asm
0x28867a  ldr.w r0,[r10,#0x2c]  ; L2CAP channel's connection record
0x28867e  ldrb.w r1,[r0,#0xc9] ; connection record byte
0x288682  cmp r1,#2
0x288684  bne.w 0x289772      ; !=2: Classic security path
; ==2 falls through:
0x288688 ...                  ; set up remote/PSM, is_originator=0
0x2886a2  bl 0x285ec8        ; l2ble_sec_access_req
...
; !=2 branch:
0x289772  adds r0,#0x20
0x289774  bl 0x24eedc        ; BTM_SetLinkPolicyActiveMode
...
0x2897b4  bl 0x258e68        ; btm_sec_l2cap_access_req
0x2897b8  cmp r0,#1
0x2897c4  bl 0x290f98        ; l2cu_send_peer_connect_rsp
```

Exact M3 mini-debug symbol results:
- `0x285ec9` (Thumb bit set), 252 bytes, mangled `_Z20l2ble_sec_access_reqRK10RawAddresstbPFvS1_hPvhES2_` → **`l2ble_sec_access_req(...)`** at code VMA `0x285ec8`.
- `0x258e68`: **`btm_sec_l2cap_access_req(...)`**, the previously verified Classic security request.
- `0x24eedc`: **`BTM_SetLinkPolicyActiveMode(...)`**, immediately preceding the Classic candidate B check.

**Supported interpretation:** The byte at `connection_record + 0xC9` controls a **LE-security vs Classic-security codepath** at this L2CAP CSM site. The `==2` branch uses an explicitly named `l2ble_*` security function; the `!=2` branch leads to Classic BTM security handling. It is therefore not a PIN/bond success flag, and should not be labeled a DS3-specific authorization state. The structural field name (e.g. `transport`) remains unverified against this vendor build's original C++ type layout, though branch semantics strongly support a transport/protocol discriminator.

### Implications for DS3

DS3's already-recorded HID Control PSM 0x11 incoming request uses BR/EDR Classic semantics. The **Classic branch** is the appropriate target for further *offline* state/event predecessor analysis, not `l2ble_sec_access_req`. This narrows the static research and rules out accidental interventions on Bluetooth LE. It still does **not prove** that the actual recorded DS3 attempt executed this particular machine-code callsite `0x2897b4`, nor diagnose HCI Authentication Complete 0x22.

Reproduction from private matching ELF:
```sh
readelf -Ws libbluetooth.debugdata.elf | grep -E 'l2ble_sec_access_req|btm_sec_l2cap_access_req'
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x28867a --stop-address=0x2886a8 libbluetooth.so
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x289772 --stop-address=0x2897c8 libbluetooth.so
```

**Safety:** No raw binary/public MAC/keys committed, no global HID security weakening, no injection, no device changes. C4C-3 live experiment **NO_GO** remains.
