# I2/I6 — Disabled-by-default BTA → BTIF passive descriptor producer

**Status:** source-level integration *research only*, not a DS3 compatibility patch and not authorized for execution on M3. Active branch \`research/m3-ds3-compat-adapter\`, PR #52. **PR #50** reverse engineering and **PR #51** source-first build readiness remain separate.

Source pin: \`BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d\`.

## Actual source patch

\`experiments/m3-ds3-cable-session/h618_private_descriptor_probe_disabled.patch\` changes **two source paths** only when \`RETROBOX_DS3_PRIVATE_DESCRIPTOR_RESEARCH\` is explicitly defined:

1. \`system/bt/bta/hh/bta_hh_act.cc\`: \`bta_hh_get_dscp_act\` makes an **additional passive Classic HID descriptor observation** through a private, internal \`btif_hh_ds3_probe_descriptor(handle, VID, PID, bytes, length)\` call. It leaves the existing \`BTA_HH_GET_DSCP_EVT\` and BLE path unchanged and does not return a security result.
2. \`system/bt/btif/src/btif_hh.cc\`: a dedicated internal consumer copies a **bounded, fixed-size POD payload** into the private \`btif_transfer_context_checked_bytes\` introduced by \`h618_checked_bytes_disabled.patch\`. The probe carries handle, VID, PID and descriptor bytes, and reports only handle/length to debug logs on the JNI thread; it never triggers \`UHID_CREATE\`, Java admission or L2CAP approval.

Both patches require the same **unset** feature macro to enable their additions. The second patch **depends** on the first: attempting to enable the probe without applying the previous checked-bytes helper would yield an unresolved symbol. Feature enablement is **not approved**. The emitter's direct BTA→BTIF function dependency needs full-tree link review; the available host test cannot prove the real build accepts this layering.

**Important:** Observing HID after BTA GET_DSCP is not a security fix. The historical DS3 attempt times out at Bluetooth authentication (HCI status \`0x22\`) **before successful HID device descriptor delivery**. Therefore the passive probe may never fire for DS3 on today's M3; it is merely source-shaped plumbing needed if subsequent native admission research can safely reach the downstream stage.

## Verification and safeguards

- All **three patch hunks** and their original context were matched line-by-line against the exact pinned H618 files through GitHub. Full \`git apply --check\` on an entire H618 checkout **was not run**, because no matching source checkout is present in this execution environment.
- A C++17 compilation using the **same BTIF function source** under stand-in scheduler and native callback macros passed strict GCC 14.2.0 \`-Wall -Wextra -Werror -pedantic\` **10/10 host assertions**, including ASan+UBSan: nullptr, zero/oversized descriptor, failed mock post, known VID/PID/handle/length, immutable copied bytes after producer mutation, callback delivery and invalid length rejection.
- \`test_h618_private_descriptor_probe_patch.py\` in this repository extracts the actual additions from the committed patch and compiles them with a fake scheduler; it is wired into \`run_cpp_host_tests.sh\`. **The exact committed Python script and a full Android build were not independently executed in this turn**; the local C++ test compiled an exact manually copied BTIF block. Keep this distinction explicit.
- The new 4096-byte fixture limit, 4104-byte POD size and private callback event \`0x7f52\` are **research constants**, not validated DS3 descriptor sizes, registered public BTA event IDs, or stable ABI values. No callback data is claimed to be a secure session capability.
- The payload contains **no ACL/HID epoch**. HID handle reuse remains a real authorization design blocker. VID/PID and claimed radio address are spoofable; do not treat the observation as peer authorization.
- No original security masks, registered HID PSM requirements, Java \`BOND_BONDED\` gates, public HAL ABI or normal bonded HID behavior are modified by the disabled patch. Under flag-off preprocessing, all new code is excluded.
- No raw controller MACs, pairing logs, LinkKeys, firmware, extracted OEM binaries or Android APKs are committed.

## Root cause is still upstream

Pinned H618:
- [\`hidh_conn.cc:95–117\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L95-L117) registers both Classic HID Control 0x11 and Interrupt 0x13 with \`BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT\`.
- [\`l2c_csm.cc:295–310\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_csm.cc#L295-L310) calls \`btm_sec_l2cap_access_req(peer,psm,false,callback,ccb)\` before channel admission and emits pending for \`BTM_CMD_STARTED\`.
- [\`btm_sec.cc:1701–1737\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L1701-L1737) still knows PSM and direction **before** security requirement flags are passed to \`btm_sec_l2cap_access_req_by_requirement\`, which drops PSM. Any real scoped CablePairing research must assess that branch, CCB callback lifetime, BR/EDR-only restriction, ACL epoch, USB enrollment provenance, MAC-spoof bounds and the Java gate.
- Returning \`BTM_SUCCESS_NO_SECURITY\` indiscriminately for HID, globally lowering service security, inventing a link key or ignoring Java's bond policy is **not** a legitimate implementation of a safe compatibility scope.

## Engineering decision

**PASS:** disabled source-shaped observer and bounded copy semantics under stand-in test. **NO_GO:** real native nonbonded HID admission, secure identity/session proof, on-device target work, \`libbluetooth.so\` installation or claiming wireless success.

**Priority next:** stop extending downstream passive plumbing. Work at the **BTM/ACL and Java admission boundaries** where the real HCI authentication fails. Define a source-level, fail-closed *observation-only* branch at \`btm_sec_l2cap_access_req\` with no changes to authentication result, plus a demonstrably scoped real USB enrollment provenance and session correlation design. Do not make a live relaxation until separately approved. The full matching H618 BSP on the owner host remains a build NO_GO per PR #51.

Reproduce the source-only tests in a checkout:
\`\`\`bash
python3 experiments/m3-ds3-cable-session/test_h618_private_descriptor_probe_patch.py
# If you have an exact checkout of the PINNED public H618 tree, inspect patches:
git apply --check /path/to/h618_checked_bytes_disabled.patch
git apply --check /path/to/h618_private_descriptor_probe_disabled.patch
\`\`\`
If testing both with git apply, account for the first patch's changes, and never apply to a live device or enable the flag without review.
