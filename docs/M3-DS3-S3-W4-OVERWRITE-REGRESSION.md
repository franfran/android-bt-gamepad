# BTA w4_evt overwrite — deterministic offline reproduction

Pinned source: `BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`, `system/bt/bta/hh/bta_hh_act.cc:1015-1058`. Within the success branch of `HID_HostWriteDev`, multiple operation types assign the **same** `p_cb->w4_evt = event` without an outstanding-operation check at that site.

`experiments/m3-source-first/test_bta_w4_overwrite.cc` creates two minimal host models:

1. `LegacyBta` reproduces the assignment: Kernel SET then HAL GET before a handshake means GET overwrites SET's event class. One handshake then sees GET; SET no longer has a matching tag.
2. `GuardedBta` demonstrates a conceptual guard *before* sending, preventing that overwrite. A synchronous failed write does not claim ownership.

The existing sanitized CI host test runner executes both this regression and the transaction owner model.

## Important scope limitations

This **does not** prove those two writes can actually interleave on the M3. The host reproduction deliberately chooses that ordering and does not model BTA queues, remote HID behavior, transport errors or Android threading. A simple guard also does **not** solve all issues: non-UHID writers need shared ownership, stale callbacks need correlation, synchronous errors must be reported, and a blocked request needs an explicit timeout/lifecycle response. Never use the guard snippet as a deployable vendor patch or interpret a successful host test as UHID completion support.

Next source proof: audit all callers of `BTA_HhSetReport` and relevant BTA state transitions; design a serialized command queue and explicit transaction-tag/lifecycle contract before editing public BSP source. Three independent gates remain unresolved; no live M3 operations approved.
