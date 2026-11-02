> **SUPERSEDED / NOT SAFE TO DEPLOY (v1):** This original research fence has a check-then-write TOCTOU window and `Revoke` unblocks fd before verified close. Do not enable or apply it for admission. See [v2 quarantine / atomic writer](M3-DS3-I2-I6-UHID-LIFECYCLE-V2-QUARANTINE.md). The prior host tests do not prove a safe runtime gate.

# I2/I6 — H618 UHID_CREATE / UHID_INPUT candidate fence (default OFF)

**PR:** #52, branch \`research/m3-ds3-compat-adapter\`. **Source pin:** \`BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d\`. **Deployment:** NO_GO. No M3 operation, no modified Bluetooth security requirements, no new bond or working DS3 radio session.

## Source-confirmed kernel event path

The existing H618 \`system/bt/btif/co/bta_hh_co.cc\` has a common native kernel handoff:
- [\`bta_hh_co_send_hid_info\` ~L505–550](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L505-L550) constructs \`UHID_CREATE\` and calls \`uhid_write(p_dev->fd, &ev)\`. **On nonzero write result, stock code closes the fd and sets \`p_dev->fd = -1\`.** A research deny fence must therefore guard before \`UHID_CREATE\` to avoid erroneously treating deliberate denial as a corrupted descriptor.
- [\`bta_hh_co_data\` ~L456–490](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L456-L490) receives HID report, resolves \`dev_handle\` to the current BTIF device, and eventually calls \`bta_hh_co_write(fd,report,len)\`; [\`bta_hh_co_write\` ~L292–305](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L292-L305) constructs \`UHID_INPUT\` and calls the same \`uhid_write\`. Some other paths also use \`bta_hh_co_write\`, so its final write barrier is more comprehensive than a single descriptor callback.
- [\`uhid_write\` ~L62–83](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L62-L83) is the common writer to \`/dev/uhid\`. Normal \`UHID_DESTROY\` and other non-CREATE/non-INPUT messages must not be stopped by the candidate fence.
- [\`btif_hh.cc BTA_HH_GET_DSCP_EVT\` ~L951–984](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L951-L984) uses shared mutable \`p_curr_dev\` and sends a descriptor before asynchronous Java Handler \`okToConnect\` is a proven pre-UHID approval boundary.

## New research patch (inert unless explicitly built AND registered)

\`experiments/m3-ds3-cable-session/h618_uhid_candidate_fence_disabled.patch\` has **3 source hunks** in \`system/bt/btif/co/bta_hh_co.cc\` and one new header \`system/bt/btif/co/retrobox_candidate_uhid_fence.h\`.

Feature macro: \`RETROBOX_DS3_UHID_FENCE_RESEARCH\` is **not defined** in any build configuration. Without it the original source compiles unchanged.

When explicitly enabled in a future *research* build, it introduces a process-local, bounded \`retrobox::CandidateUhidFence\` and opt-in functions:
- \`retrobox_register_uhid_candidate(FenceTicket{fd, HID handle, ACL epoch, request_id})\`
- \`retrobox_revoke_uhid_candidate(exact_ticket)\`

**Neither function has a caller in this patch**. The new registry starts empty: enabling the flag alone cannot identify a cable candidate or block an unregistered device. An eventual trusted Native producer must classify and register a candidate **before** any descriptor or input event, and must reject the entire candidate connection if registration fails. It must also ensure ticket-bound cleanup on actual fd close/disconnect, and prevent unknown/stale fd reuse. The current research patch does not implement those prerequisites.

For an **already registered** candidate fd, a guard before \`UHID_CREATE\` returns early (avoiding stock fd close), and the final \`uhid_write\` intercepts \`UHID_CREATE\` / \`UHID_INPUT\`, returning \`-EACCES\` without calling \`write(fd,...) \`. Other unregistered devices and other UHID event types keep their original write path. There is **no approval/grant operation**, no Java response wired into this registry and no special handling of a \`BOND_BONDED\` or unbonded candidate at BTM.

### Constraints — why this is NOT a security enforcement rollout

- **Not a universal pre-UHID gate**: no Native candidate classifier/registry caller exists. Unregistered devices keep using existing code. Registered candidates are always blocked, never conditionally approved. This is a testable *final kernel write barrier location*, not the completed authorization workflow.
- **fd and HID handle are reusable**. Registration rejects collisions, and exact-ticket \`Revoke\` refuses stale ACL/request IDs in the host model; however the real source needs a trusted lifecycle owner to ensure registration-before-event and revocation-only-after-closure. Premature \`Revoke\` could unblock an existing fd. Registration failure must never fall back to a candidate bypass.
- **Threading**: \`bta_hh_co_data\` and the UHID polling thread can be concurrent with control path events. The model's registry therefore uses \`std::mutex\` for lookups and writes, but actual stack lock order, teardown races and fd reuse are **not verified**.
- **Native/Java**: PR #52's separate [deny-only JNI/Java patch](M3-DS3-I2-I6-H618-JNI-JAVA-DENY-ONLY-SEAM.md) has no caller and no effective BTM veto. It is not connected to this registry.
- **Actual radio blocker**: prior M3 HCI authentication timeout \`0x22\` happens upstream of successful HID descriptor delivery. This UHID hook cannot solve that failure, prove a matching DS3 radio station, or configure Sony feature report \`0xF4\`.
- **Build**: no matching full Android BSP, target ABI verification, Android Soong compilation or live runtime test. Do not enable the research flag, replace \`libbluetooth.so\`, restart service, push APK, or merge without new separate owner authorization.

## Offline checks performed

Files:
- \`candidate_uhid_fence.h\`
- \`test_candidate_uhid_fence.cc\`
- \`verify_h618_candidate_uhid_fence.py\` (optional full-BSP \`git apply --check\`)
- \`run_cpp_host_tests.sh\` updated to run the host test.

**Actual local execution with byte-identical GitHub files** (both Git blob SHAs matched the committed objects):
\`\`\`text
g++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread \
  test_candidate_uhid_fence.cc -o fence_test
./fence_test
53/53 PASS (candidate-only UHID fence host model)

g++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  test_candidate_uhid_fence.cc -o fence_sanitized
ASAN_OPTIONS=detect_leaks=1 ./fence_sanitized
53/53 PASS (candidate-only UHID fence host model)
\`\`\`

53 **assertions** test ordinary untracked path unaffected, registered candidate CREATE/INPUT denied, unrelated UHID type not denied, duplicate fd/HID handle registration rejection, stale exact-ticket revocation refused, slot exhaustion and bounded recovery, invalid ticket inputs and serialized multi-thread reads. These are not real descriptor parsing or Bluetooth tests.

**Source context audit:** all **3 modified-file hunks** verified against the exact pinned H618 source with correct original/new line counts and cumulative line offsets; the newly added source header was checked byte-for-byte against the host-tested committed header. The initial overlapping patch hunks were consolidated before final verification. An exact full-tree \`git apply --check\` and a source-integrated Android build have **not** been run. The committed Python verification script is provided for reproducibility but has not itself been executed in this turn.

## Next integration gate

Only if a trusted, reviewable Native provenance signal can be created, the design needs **classification-before-descriptor** and ownership before entering BTA/BTIF, request-bound Native↔Java response, no unbonded MAC-only trust, explicit close-and-retire lifecycle, and normal bonded HID regression on a matching target build. **NO_GO** for any device-facing action until source and safety conditions are met.

**Conclusion:** final kernel write path identified and offline guarded candidate rejection PASS; complete DS3 wireless compatibility and any real authorization remain **NOT IMPLEMENTED**. Draft PR #52 stays open, PR #50/51 independent.
