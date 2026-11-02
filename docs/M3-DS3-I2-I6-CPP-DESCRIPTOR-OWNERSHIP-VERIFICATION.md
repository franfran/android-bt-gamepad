# I2/I6 — Source-backed descriptor ownership and compiled C++ host regression

**Pinned source:** `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. Scope: offline C++17 research only, no actual M3/H618 Bluetooth security patch, Bluetooth commands, Java callback, production radio proof, or deployed firmware.

## Trace the descriptor pointer from SDP through native callback

1. [`stack/hid/hidh_api.cc:105–132`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_api.cc#L105-L132): HID descriptor parsed from SDP; the initial `dsc_list` points into SDP attribute storage. This is a **borrowed** pointer.
2. [`bta/hh/bta_hh_utils.cc:168–199`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_utils.cc#L168-L199): BTA's HID device CB duplicates descriptor bytes using `osi_malloc` + `memcpy`. [`bta_hh_clean_up_kdev:105–132`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_utils.cc#L105-L132) frees that CB-owned descriptor. There is therefore **already a BTA ownership boundary**, not an always-dangling SDP pointer.
3. [`BTA_HhGetDscpInfo:288–296`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_api.cc#L288-L296) puts the HID handle into the request's `layer_specific`; [`bta_hh_main.cc:322–355`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_main.cc#L322-L355) resolves the CB by this handle.
4. [`bta_hh_get_dscp_act:905–911`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_act.cc#L905-L911) then emits the descriptor **without** a handle, by casting `&p_cb->dscp_info`. [`tBTA_HH_DEV_DSCP_INFO`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/include/bta_hh_api.h#L206-L230) has descriptor metadata, not a handle or ACL generation.
5. [`btif_hh.cc:1105–1133`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L1105-L1133) calls `btif_transfer_context(..., NULL)` on descriptor events. [`btif_core.cc:127–150`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_core.cc#L127-L150) shallow-copies the event structure if its copy callback is null. The pointed-to descriptor bytes are **not** independently owned by the event.
6. [`btif_hh.cc:951–984`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L951-L984) associates the event with shared `p_curr_dev` before calling `bta_hh_co_send_hid_info` → `UHID_CREATE`.

**Important precedent:** [`BTA_HhAddDev:305–334`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/bta/hh/bta_hh_api.cc#L305-L334) already allocates a contiguous event payload and deep-copies descriptor bytes for an *unrelated maintenance message*. It demonstrates a native source pattern for ownership, **not** proof that the GET_DSCP event today does the same. Do not simply enlarge `tBTA_HH_DEV_DSCP_INFO` while producer still casts `&p_cb->dscp_info`: that can cause out-of-bounds structure reads.

### Source-level readiness finding

A real delayed CablePairing admission would need to preserve the existing normal bonded HID path, and introduce a distinct private BTA→BTIF event envelope with event-bound HID handle + newly minted runtime generation **and owned descriptor bytes**. It must ensure correct allocation, transfer, cleanup, cancellation, and no use after BTA CB reuse or disconnect. The exact native↔Java approval handshake **does not exist yet** and cannot be inferred from address/state.

## New C++17 host-only implementation and tests

- `experiments/m3-ds3-cable-session/session_descriptor_envelope.h`
- `experiments/m3-ds3-cable-session/session_descriptor_envelope.cc`
- `experiments/m3-ds3-cable-session/test_session_descriptor_envelope.cc`
- `experiments/m3-ds3-cable-session/run_cpp_host_tests.sh`

Model explicitly stores `Ticket{hid_handle,generation}` and an owned `std::vector<uint8_t>` snapshot. It retains **no borrowed raw descriptor pointer** after `ReceiveDescriptor`. It rejects stale/reused handle events, Java denial, malformed fixture inputs, duplicate descriptors, and UHID input until both proposed admission gates and kernel readiness. Ordinary bonded devices are **not represented**; this is not a drop-in API.

**Host verification:** compiled with GCC 14.2.0, `-std=c++17 -Wall -Wextra -Werror -pedantic`; **17/17 passed**. Compiled and reran the same source with `-fsanitize=address,undefined -fno-omit-frame-pointer`; **17/17 passed**. Tests include descriptor-first/Java-first, producer-memory mutation, two-device interleaving, HID handle reuse/stale callbacks, denial cleanup, report gating and post-close revocation.

To rerun in checkout (shell script text may need executable permission):
```sh experiments/m3-ds3-cable-session/run_cpp_host_tests.sh
```

Or build with:
```bash
cd experiments/m3-ds3-cable-session
g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  session_descriptor_envelope.cc test_session_descriptor_envelope.cc -o /tmp/ds3-envelope-host-test
/tmp/ds3-envelope-host-test
```

## Meaning and limits of the result

- **PASS (model only):** robust epoch/handle correlation and independent descriptor lifetime are straightforward to implement in host C++ and covered by 17 deterministic unit tests.
- **NOT PROVEN:** an actual H618 BTA/BTIF callback carrying this envelope; allocation/free on the real JNI threads; actual ACL generation and HID handle assignment; correct Android HAL/Java authorization response; precise DS3 descriptor validator; radio MAC spoof resistance; security exemption safety; real system image build.
- `native_policy_passed`, `fixture_gamepad_valid` and `fixture_report_valid` are **externally supplied symbolic booleans**, not cryptographic proof or genuine HID parsers. Fixture max-length 4096 is only a test parameter and **NOT** a source-verified production limit.
- H618 reference source is not guaranteed ABI-identical to original M3 firmware. Build preflight for PR #51 previously failed because owner host lacked the BSP source directory. No inference of target compilation.

**Next gate:** audit real source dispatch/copy/cleanup rules for any new internal envelope, propose an opt-in private event type and event-bound Java response contract *without* altering stable HAL ABI, but do not attempt deployment without exact compatible source/build and explicit owner security-risk approval. No M3 actions, unbonded global HID security, fake bond, or merge.
