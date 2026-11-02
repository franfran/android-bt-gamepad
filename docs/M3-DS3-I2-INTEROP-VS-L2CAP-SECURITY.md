# I2: interop feature matching is not L2CAP security policy

Pinned BSP: `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. Evidence is source-only; OEM runtime equivalence is unproven.

## Verified source evidence
- [device/include/interop.h lines 30–120](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/device/include/interop.h#L30-L120) defines workarounds such as `INTEROP_KEYBOARD_REQUIRES_FIXED_PIN`, `INTEROP_HID_PREF_CONN_SUP_TIMEOUT_3S`, `INTEROP_HID_HOST_LIMIT_SNIFF_INTERVAL`. No dedicated DS3 security exception appears in this enum.
- [device/src/interop.cc lines 47–94](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/device/src/interop.cc#L47-L94): `interop_match_addr` checks fixed/dynamic entries; `interop_database_add` stores an address prefix and feature. Address match only is **not** authentication or verified device identity.
- [btif/src/btif_dm.cc lines 727–767](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_dm.cc#L727-L767) performs restricted auto-pair PIN `0000` for certain device classes and the keyboard-specific workaround, but neither branch constitutes DS3 sixpair admission.
- [btif/src/btif_dm.cc lines 818–843](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_dm.cc#L818-L843): `BOND_TYPE_TEMPORARY` is one SSP JustWorks classification, not proof that native DS3 Classic HID is eligible or that Java `BOND_BONDED` gate is satisfied.
- [stack/btm/btm_sec.cc lines 461–517](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L461-L517) assigns and normalizes PSM service security flags; encryption implies authentication.
- [stack/btm/btm_sec.cc lines 1488–1611](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L1488-L1611) checks peer security status, serializes requests and can enforce authentication/encryption for SM4 devices.
- [stack/btm/btm_sec.cc lines 1701–1736](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L1701-L1736): `btm_sec_l2cap_access_req` finds a registered PSM service's security flags and delegates to `btm_sec_l2cap_access_req_by_requirement`. It does **not** consult `interop_match_addr` at this callsite.

## Interpretation
**PROVEN:** Existing interop workaround list and L2CAP security decisions are separate mechanisms in inspected callsites; inserting a new feature enum alone cannot change service security admission.

**INFERRED:** A safe source-level per-device DS3 adapter would need a narrowly scoped, authenticated enrollment/identity design and carefully reviewed integration at actual transport/security, Java admission and kernel input boundaries. Global HID security downgrade is not acceptable.

**UNTESTED:** Other code paths using interop, exact OEM variant, possible existing privileged extensions, viable coexistence of daemon with Fluoride, authorization of sixpair-enrolled devices, runtime HCI 0x22 cause.

## Important caveat
The four-digit PIN/temporary-bond code is **not** a recommended workaround; it has different semantics and cannot be treated as a sixpair fix. Never create fake `BOND_BONDED` state or mark an unauthenticated link encrypted.

## Next
Trace specific HCI authentication failure propagation and actual Java `HidHostService` entry/virtual-unplug path; enumerate candidate per-device admission requirements and falsification tests offline. Then evaluate whether a source-level adapter could solve gates A/B/C with fewer changes than PR #51, without claiming a plugin hook exists.

No M3 runtime action, security flag changes, live probes, firmware/build deployment, or merge.
