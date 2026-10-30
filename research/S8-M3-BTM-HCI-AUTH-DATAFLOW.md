# S8 — M3 BTM security procedure constructs the HCI Authentication Requested command

**Original evidence:** SHA-256 verified owner-uploaded ARM32 M3 `libbluetooth.so` (SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`), inspected offline. The proprietary ELF is not committed.

This result closes another specific **static** edge after PR #38's L2CAP state/event → Classic BTM security mapping.

## Exact native caller → HCI command builder

- The recovered original M3 symbol table identifies `btm_sec_execute_procedure(tBTM_SEC_DEV_REC*)` at Thumb code VMA `0x257c04`, with 1792-byte function size.
- At **`0x2580c0`**, the function directly calls **`btsnd_hcic_auth_request(uint16_t)`** at `0x27c998`, after loading the device ACL handle from `[r4+0x10]` into `r0` at `0x2580b8`.
- The path leading to this call checks security flags at `0x2580a2..0x2580b4` and sets a security state byte at `[r4+0x129]` just before the call. This code is conditional; the runtime selection for the specific DS3 capture is **unverified**.
- At `0x27c9ae`, the actual builder loads **HCI opcode `0x0411`**, and at `0x27c9b2` writes it to the outgoing HCI command packet. `0x0411` is the **Authentication Requested** opcode observed in the historical DS3 btsnoop record #151.
- Original M3 symbol `btm_sec_auth_complete(uint16_t,tHCI_ERROR_CODE)` begins at `0x25b5c4`. At `0x25b5e6`, this handler copies its **second argument, HCI status `r1`**, into a local byte. This is a concrete native status-handling entry, consistent with the HCI event #159 reporting `0x22`. It does **not** establish which downstream branch the recorded DS3 attempt followed.

## What changed

The previous evidence chain stopped at `btm_sec_execute_procedure`. The newly verified link is:

```text
BTM_SetSecurityLevel (registration)
  -> L2CAP incoming peer CONNECT_REQ state/event branch
  -> btm_sec_l2cap_access_req
  -> btm_sec_l2cap_access_req_by_requirement
  -> btm_sec_execute_procedure
       [conditional auth branch]
       -> btsnd_hcic_auth_request(handle)
            -> HCI command opcode 0x0411, Authentication Requested

Controller eventually returns Authentication Complete status 0x22
  -> known native status handler: btm_sec_auth_complete(handle, status)
       [exact DS3 runtime branch not established]
```

**Important limitation:** This is machine-code proof of an available command-construction route, not live tracing of a DS3 authentication attempt. HCI status `0x22` denotes an LMP response timeout, but a static host binary cannot establish whether DS3, M3 controller firmware, packet loss, timing, or a legacy pairing interoperability issue is responsible. A successful PIN reply command is merely host-controller acceptance, not Bluetooth link authentication success.

The direct source-level auth branch **does not establish that bypassing it would permit usable HID**, and globally relaxing the HID 0x36 mask would weaken other controllers. A local trust enrollment needs design/verification before any safe DS3 exception.

## Offline verification

```sh
python3 experiments/s8-hci-auth/verify_hci_auth.py /private/local/libbluetooth.so
```

The script fails closed unless the ELF hash, ARM32 header, and exact raw Thumb instructions at the callsite, command builder and completion handler all match. No runtime interaction, injection, firmware replacement, Bluetooth service restart or raw key/MAC publication.

**Next genuine research task:** map the security flags/branch predicates at `0x2580a2..0x2580b4` to authenticated device state, and document where the host's `0x22` is propagated and bond is rolled back. This is still separate from the firmware-level LMP timeout's actual cause.

**Live authorization:** C4C-3 remains **NO_GO**.
