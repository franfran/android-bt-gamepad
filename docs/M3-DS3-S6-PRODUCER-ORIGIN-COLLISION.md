# S6 producer-collision and error-boundary audit

Pinned H618 Android12 source `250eabfc529518b7f26432663ed0a867ab2f625d`.

## Verified direct producer collision

`btif/co/bta_hh_co.cc:121-130` sends `UHID_OUTPUT` with type `UHID_FEATURE_REPORT` through `btif_hh_setreport`, **the same** send wrapper used for `UHID_SET_REPORT` feature/output/input cases at lines 164-187. Also, the Java HAL calls `BTA_HhSetReport` via `btif_hh.cc`. The native BTA consumer has no origin field and receives no UHID request ID. Consequently a simple FIFO of *kernel request IDs alone* would wrongly attribute output/HAL handshakes.

`btif_hh_setreport` at `btif/src/btif_hh.cc:630-639` returns `void`; `create_pbuf` allocation failure logs and exits without a BTA message. It is impossible to correctly recover this error by waiting for BTA callbacks that were never queued.

`UHID_FEATURE` GET uses a separate request-ID queue, but that is **not** a safe model to clone for SET without source-aware dispatch and response attribution.

## Source integration acceptance criteria

1. Tag producer origin **at ingress**, before shared `btif_hh_setreport` and BTA queue: kernel UHID SET, kernel OUTPUT, Java HAL, GET, protocol. Capture `ev.u.set_report.id` only from UHID SET.
2. A local allocation failure must produce a request-specific *negative* result through a verified safe path; do not wait for remote handshake.
3. Admission must occur **before sending**. A global guard in BTA after request enqueue cannot repair missing producer metadata.
4. Source-aware per-handle ownership must consider multiple classic HID devices and disconnected generations. Do not claim `w4_evt` proves unique handshake identity.
5. A real `UHID_SET_REPORT_REPLY` requires the complete event container and correct kernel ID/type; mapping nonzero errors to Boolean failure was verified in upstream Linux v5.4, but the M3 downstream kernel remains to compare.

## Current evidence

The existing `uhid_ingress_id_EXPERIMENTAL.patch` only captures a local variable then discards it. It is **not** end-to-end propagation. The existing `bta_w4_guard_EXPERIMENTAL.patch` remains a global, nondeployable experiment. All experimental patches stay off the M3 and out of merged source. Authenticity, Java bond and ARM32 Soong/ABI gates remain unresolved.
