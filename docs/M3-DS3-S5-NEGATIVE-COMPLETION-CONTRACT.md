# S5: Request-specific negative completion contract (host-only)

2026-11-01. Pinned source `BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. Experimental C++ model `negative_completion_model.h`; runner `test_negative_completion_model.cc`.

## Findings in pinned Fluoride

- `btif/co/bta_hh_co.cc:165-189`: UHID SET ID is dropped at ingress; forwarding report bytes alone cannot later identify the kernel waiter.
- `btif/src/btif_hh.cc:630-639`: `create_pbuf` allocation failure simply returns void, leaving no correlated UHID negative completion.
- `bta/hh/bta_hh_main.cc:223-245`: invalid-handle path generates an application error after freeing payload, bypassing SET co-callout.
- `bta/hh/bta_hh_act.cc:1031-1042`: local HID transport send failure generates app callback, not SET co-callout.
- `stack/hid/hidh_conn.cc:742-750,824-827`: ACL-down/congestion/L2CAP failure can reject dispatch. These are LOCAL failures, not remote handshake.
- `bta/hh/bta_hh_act.cc:662-674`: remote SET handshake supplies status but not originating request ID.

## Implementable contract prerequisites

1. Capture `ev.u.set_report.id` and distinguish request origin (kernel SET versus UHID OUTPUT / Java HAL). Lifetime must be bounded per device and connection generation. Do not confuse `rpt_id` with UHID ID.
2. Preserve origin identity through BTA queue and local-send error paths without changing only one end of the shared `tBTA_HH_CMD_DATA` ABI.
3. Exactly one **negative-completion observation** may be created for a known pending kernel SET on allocation, invalid handle, local transport error, or known remote negative handshake.
4. On timeout or disconnect, quarantine handle/session and suppress any stale callback. Do not convert a stale handshake to successful reply. On disconnect, kernel teardown or kernel timeout may be required; response semantics need source/kernel validation.
5. A native kernel `UHID_SET_REPORT_REPLY` writer must not be enabled until mapping of original ID and error encoding is confirmed against the M3 kernel and all callbacks are disambiguated.

The host model tests identity preservation, handle/generation rejection, exactly-once failure observation, and quarantine. Its `NegativeReceipt` is deliberately **not** an actual UHID reply or errno mapping. Permanent quarantine keeps this model fail closed but not suitable for continuous DS3 operations.

**Still NO_GO:** experimental global BTA guard is unfit for deployment; original native HCI 0x22 auth and Java bond-gate independently unresolved; ARM32 Soong not built. No M3 operations, binary writes, library replacement, security weakening or PR merge.
