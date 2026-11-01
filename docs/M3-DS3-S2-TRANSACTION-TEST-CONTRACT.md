# S2: UHID SET_REPORT offline C++ transaction gate

This is an **offline model**, not deployable Android stack code. Build on host:

```sh
c++ -std=c++17 -Wall -Wextra -Werror -pedantic experiments/m3-source-first/set_gate_host_test.cc -o /tmp/m3-set-gate-test
/tmp/m3-set-gate-test
```

Tests: unsolicited callback, full request ID, no concurrent requests per device, deadline boundary, raw negative status, duplicate callback, independent handles, timeout and late callback, no recycling after quarantine, disconnect/reconnect denial, zero/overflow timeout. The model deliberately has **no reset** for poisoned device identities.

**Fundamental limitation:** `bta_hh_co_set_rpt_rsp(uint8_t dev_handle, uint8_t status)` does not return a UHID ID or session epoch. Even when only one request is outstanding, a late callback from a *previous completed request* could be misattributed to the current request if duplicate or delayed callbacks are possible. This model proves only local invariants; it does not establish that native Fluoride callbacks are bijective or ordered, nor does it produce a kernel reply.

**Design decision:** Do not yet wire a FIFO to `UHID_SET_REPORT_REPLY`. First trace source paths for `btif_hh_setreport`, `bta_hh_api` and `w4_evt`, including error/close paths. If strict callback association cannot be established, propagate explicit transaction tokens through the native state machine or otherwise fail closed. A secure per-DS3 native auth exception and Java bond-policy solution remain separate independent gates; no global L2CAP change.

**Execution status:** source reviewed; host compilation/runtime evidence should be recorded explicitly, not inferred from GitHub commit.
