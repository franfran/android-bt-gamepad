# I2/I6 — Descriptor callback identity loss, pointer lifetime, and minimal source change boundary

**Status:** source-proven gaps and offline-only prototype. Neither an actual Android patch nor an authorization to bypass Bluetooth security. PR #52 stays Draft; PR #50 and PR #51 remain independent.

Source pinned: \`BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d\`.

## 1. Precisely where descriptor identity disappears

1. [\`BTA_HhGetDscpInfo(dev_handle)\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_api.cc#L288-L295) **has a HID handle** and writes it into \`p_buf->layer_specific\`.
2. [\`bta_hh_hdl_event()\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_main.cc#L322-L355) uses \`layer_specific\` to resolve the corresponding \`tBTA_HH_DEV_CB\`, then dispatches to \`bta_hh_get_dscp_act\`.
3. [\`bta_hh_get_dscp_act()\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L905-L911) emits \`BTA_HH_GET_DSCP_EVT\` using **\`(tBTA_HH*)&p_cb->dscp_info\`**, not an envelope with the HID handle.
4. [\`tBTA_HH_DEV_DSCP_INFO\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/include/bta_hh_api.h#L206-L230) contains VID/PID, version, SSR fields, country, flag, descriptor, but **no BD_ADDR, HID handle, ACL generation or ticket**. Its [union member](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/include/bta_hh_api.h#L300-L312) is solely \`dscp_info\`.
5. [\`bte_hh_evt()\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1105-L1133) transfers \`sizeof(tBTA_HH_DEV_DSCP_INFO)\` for this event via \`btif_transfer_context(..., NULL)\`.
6. [BTIF descriptor handler](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L951-L984) then picks **shared mutable \`btif_hh_cb.p_curr_dev\`** to select address, fd and UHID destination. When another OPEN changes this pointer, there is no event-level check proving the descriptor belongs to that selected device.

**Verdict:** source-proven identity omission; possible cross-device interleaving hazard is a **test hypothesis**, not a demonstrated exploit or measured race on M3. Simply adding a \`handle\` to the end of \`tBTA_HH_DEV_DSCP_INFO\` without changing the callback producer is **unsafe**: producer currently casts an existing \`p_cb->dscp_info\` into the callback, so enlarging the transferred struct risks reading beyond that object. Any envelope must be explicitly constructed by BTA and consumed consistently by BTIF.

## 2. Separate lifetime issue if descriptor must wait for Java

[\`btif_transfer_context()\` at btif_core.cc:127–150](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_core.cc#L127-L150) uses \`memcpy\` when the optional deep-copy callback is NULL. For descriptor events [\`bte_hh_evt()\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1117-L1132) indeed passes NULL. A copied \`dsc_list\` pointer is **not an owned copy of its descriptor bytes**.

The BTA control-block descriptor may remain live for ordinary immediate handling, but there is **no basis for treating its borrowed pointer as safe across a newly introduced Java wait / disconnect / reconnect**. A deferred candidate must snapshot validated bytes into explicitly owned storage with a cleanup path. Resolve deep-copy ownership, bounds, cancellation, and cleanup independently of event identity.

## 3. Source change touchpoints (proposal only, no patch committed)

| Layer | Minimum responsibility |
|---|---|
| BTM/L2CAP and HID session | Mint/propagate trusted *runtime correlation* generation for a new ACL/HID lifetime; revoke on disconnect. It does **not** establish cryptographic DS3 identity. |
| BTA HH internal callback | Construct an explicit descriptor-response envelope containing **BTA handle plus immutable link/HID generation and descriptor metadata**. No blind cast of enlarged \`p_cb->dscp_info\`. |
| BTIF context transport | Preserve envelope and deep-copy descriptor into owned, bounded memory. Define cleanup on reject, service shutdown, stale event and timeout. |
| BTIF descriptor consumer | Resolve exact session ticket; **stop relying on \`p_curr_dev\` for cable exception**. Queue until policy gate(s) complete; do not write \`UHID_CREATE\` first. Normal bonded HID must keep working unchanged. |
| Protected Native ↔ Java bridge | Produce/consume **event-bound admission**, not \`okToConnect(MAC)\`; retain normal Java quiet-mode/policy conditions and avoid public HAL ABI assumptions. |
| UHID data/close | Enforce descriptor and report policy for this ticket before \`UHID_CREATE\` and \`UHID_INPUT\`; invalidate ticket and owned buffers on close. |

This is **multi-source-component work**, not a one-function / one-\`.so\` workaround. The M3 exact firmware ABI and full BSP build remain unverified; do not assume a compiled runtime patch exists.

## 4. New executable negative tests

Added \`experiments/m3-ds3-cable-session/descriptor_envelope_model.py\` and \`test_descriptor_envelope_model.py\`.

Model illustrates an unsafe global-current-device selector for comparison and proposes an **immutable \`Ticket(handle, epoch)\`** with per-session descriptor byte snapshot and Java admission. 12 unit tests cover both descriptor/Java arrival orders, interleaved two-device callbacks, stale handle/epoch, unapproved Native candidate, bad/empty descriptor, immutable copy vs mutable input, Java veto, duplicate descriptor/creation, and disconnect isolation.

Local host-only Python execution:
\`\`\`text
python3 -m unittest -v
Ran 12 tests in 0.001s
OK
\`\`\`
Command executed in isolated local fixture directory containing the two new files (not an Android build). The \`descriptor_valid\` and \`native_allowed\` inputs are **symbolic booleans**, not genuine descriptor parser, owner security approval, or working radio authentication. Test data \`b'gamepad'\` is illustrative, **not** a real DS3 descriptor. The "legacy" global example demonstrates what an unchecked shared pointer **could** do in an artificial schedule, not proof that Android reaches that ordering.

## 5. Next proof gate

Before C++ source change, inspect ownership/dispatch of \`tHID_DEV_DSCP_INFO.descriptor\` and whether BTIF can atomically map an event to ACL generation without changing stable HAL ABI; prototype a source-integrated, **disabled-by-default** internal envelope only when buildable source tree is ready. Java-before-UHID authorization itself requires a new asynchronous acknowledgment path whose deadlocks and latency must be analyzed. Keep existing normal bonded HID unchanged.

**Project goal:** already-working wired DS3 in M3 RetroArch, USB setup once, then PS-button wireless/reconnect without recabling. No live M3 changes, service restart, security downgrade, firmware flash, APK installation, or PR merge authorized.
