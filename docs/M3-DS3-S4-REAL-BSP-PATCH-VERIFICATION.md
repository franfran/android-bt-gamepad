# S4 pinned-source patch applicability and deployment blocker review

## Verification target

Upstream BSP commit `250eabfc529518b7f26432663ed0a867ab2f625d`, exact `bta_hh_act.cc` Git blob `bc092b68c12502d2f73a7dbab65426ab05fd28c1` (not an OEM source attribution claim).

New `test_real_pinned_bsp_patch.py` downloads that **specific public blob**, checks Git's blob-object SHA-1 with the `blob <size>\\0` header, then runs `git apply --check` and `git apply` in a temporary tree. This is a stronger test than the prior synthetic fixture: it detects upstream context drift and proves patch applicability to the actual pinned upstream file. It does NOT compile Android or check behavioral safety.

## Critical unresolved risks in experimental patch

1. **No UHID completion on rejection:** current BTA pre-send guard invokes the old app callback only. Kernel-origin SET could wait indefinitely until UHID times out, since it is not correlated with `ev.u.set_report.id`.
2. **Callback and origin ambiguity:** `w4_evt` is event class, not an ID or generation. A stale handshake following clear/reconnect may still be mistaken for a current one.
3. **Potential shared payload ownership and application callback behavior:** the experimental guard manually frees `p_data`. Compare with the normal `HID_HostWriteDev` failure path (which frees `pbuf`) and invalid-handle BTA fallback before integrating; unexpected callback state and cleanup could affect unrelated HID devices.
4. **Global scope of hypothetical guard:** it would affect *every* Classic HID device, not just a verified cable-enrolled DS3. No approved auth security or exception policy yet.
5. **Possible LE and source distinctions:** this insertion is only after the LE branch, and `tBTA_HH_CMD_DATA` does not carry a trustworthy producer identity. Do not claim complete command serialization.

## Acceptance sequence

1. Actual pinned-source patch application must PASS in CI.
2. Add C++/Soong compile checks and explicit report ownership/timeout failure propagation **before** calling it a compatibility patch.
3. Demonstrate unambiguous native transaction callback identity and safe per-device session handling. If absent, keep UHID SET reply disabled and deployment NO_GO.
4. Separately resolve native pre-auth HCI failure `0x22` and OEM Java bond/virtual-unplug policy.
5. For any real M3 test, require a separate owner approval; no deployment authorization follows from upstream patch applicability.

No M3 access, no lib replacement, no system writes, no merge.
