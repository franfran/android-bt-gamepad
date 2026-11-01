# S5 first UHID ingress source patch — identity capture only

Pinned BPI H618 Android12 public BSP `250eabfc529518b7f26432663ed0a867ab2f625d`, `system/bt/btif/co/bta_hh_co.cc` blob `c5aba4425d272dc963b6f60567d7b79fb0c18f75`.

Patch `experiments/m3-source-first/uhid_ingress_id_EXPERIMENTAL.patch` introduces a local `const uint32_t uhid_request_id = ev.u.set_report.id;` inside the existing `UHID_SET_REPORT` switch arm. It intentionally casts to void to preserve original runtime behavior while establishing a pinned upstream insertion point. The separate `test_real_ingress_id_patch.py` checks Git blob identity, `git apply --check` and `git apply` against the actual public file in an ephemeral workspace.

**This is source instrumentation groundwork only, not functional ID propagation.** The variable is local and discarded. Existing `btif_hh_setreport` calls still omit the kernel ID. There is no pending-request owner, no correlated negative completion, no handshake attribution and no `UHID_SET_REPORT_REPLY` writer. We deliberately do not fabricate these links.

Next real source patch must introduce a shared origin/session request owner between UHID reader and BTIF send; then account for BTA queue, invalid-handle and transport-failure paths, before any remote handshake is considered attributable. The BTA experimental pre-send guard remains NO_GO because it is global and strands UHID requests. No OEM/kernel ABI equivalence or ARM32 Soong build is established.

No M3 interaction, no security weakening, no changes to system files or merging. PR #51 remains Draft and PR #50 remains an independent reverse-engineering archive.
