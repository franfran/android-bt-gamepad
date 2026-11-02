# I2/I6 — BTM ↔ L2CAP HID authentication: disabled observational source patch

Workstream: RetroBox iMETBOX M3 DS3 wireless, PR #52 \`research/m3-ds3-compat-adapter\`. Reference source: \`BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d\`. No M3 runtime or matching full Android BSP compilation in this increment.

## Primary result: direct HCI authentication source path

The DS3 USB wired baseline is already confirmed operational in M3 RetroArch. The radio attempt instead fails in legacy Bluetooth pairing/authentication: HCI Authentication Complete status \`0x22\` (LMP Response Timeout) and \`BOND_BONDING → BOND_NONE\`. This describes the previously collected owner evidence, not a new hardware test.

The pinned source chain is now traced:

1. [\`hidh_conn.cc:95–117\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L95-L117) registers inbound HID Control \`0x11\` and Interrupt \`0x13\` with \`BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT\`.
2. [\`l2c_csm.cc:295–310\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_csm.cc#L295-L310) invokes \`btm_sec_l2cap_access_req(bda, psm, false, callback, ccb)\` for incoming BR/EDR L2CAP. On \`BTM_CMD_STARTED\`, a \`L2CAP_CONN_PENDING\` response may be sent.
3. [\`btm_sec.cc:1701–1737\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L1701-L1737) has the **last convenient policy entry point with both PSM and direction**. It resolves the registered service security flags and passes \`security_required\` to \`btm_sec_l2cap_access_req_by_requirement(...)\` **without the PSM**. SM4 behavior can further force incoming auth/encrypt.
4. [\`btm_sec_execute_procedure:4252–4370\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L4252-L4370) checks authentication required versus device security state and then may call \`btm_sec_start_authentication\`. It separately checks encryption and may call \`btsnd_hcic_set_conn_encrypt(..., true)\`.
5. [\`btm_sec_start_authentication:4391–4394\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L4391-L4394) emits **\`btsnd_hcic_auth_request(p_dev_rec->hci_handle)\`**; this is the source-level HCI authentication request.
6. [\`btm_sec_auth_complete:3043–3140\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L3043-L3140) processes HCI completion status and continues the BTM pairing/security flow; [\`l2c_link_sec_comp2:272–326\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_link.cc#L272-L326) resolves a **currently live CCB by the callback ref pointer** and routes BTM security callback status into L2CAP \`SEC_COMP\`, \`DELAY_CHECK\`, or \`SEC_COMP_NEG\`. Stock code normalizes \`BTM_SUCCESS_NO_SECURITY\` to \`BTM_SUCCESS\` before the status switch.

**Interpretation:** The HCI timeout is consistent with the observed source's authentication pathway, but the existing logs and source trace do **not** establish that a scoped bypass is safe, sufficient, or compatible with HID encryption, Java \`BOND_BONDED\` admission, descriptor and report handling. Also, stock BTM security results can differ from raw HCI statuses; do not equate a mock BTM status with HCI 0x22.

## New disabled-by-default two-file source patch

\`experiments/m3-ds3-cable-session/h618_btm_hid_auth_observe_disabled.patch\`:

- \`system/bt/stack/btm/btm_sec.cc\`: inside \`btm_sec_l2cap_access_req\` **after** service security requirement resolution, log **only incoming** PSM 0x11/0x13 with numeric security requirement + security mode. No peer address, USB identity, PIN, LinkKey or descriptor contents logged. Original \`btm_sec_l2cap_access_req_by_requirement\` call and its return value unchanged.
- \`system/bt/stack/l2cap/l2c_link.cc\`: inside existing matching CCB branch **before** its status switch, log the status for live HID PSM 0x11/0x13 when \`p_rcb != nullptr\`. This callback may also serve outgoing HID; it does **not** identify the radio peer or distinguish inbound/outbound by itself. The original switch and all BTM/L2CAP decisions remain unchanged.

Every new statement is guarded by **\`#if defined(RETROBOX_DS3_BTM_AUTH_OBSERVE)\`**. The flag is not defined in Android build configuration and is disabled by default. This is an **observation-only patch**; it does not enable legacy CablePairing, change bond states, fake HCI authentication, alter HID service registration, reduce security masks or send HCI commands.

### Offline regression verification

Added \`experiments/m3-ds3-cable-session/test_h618_btm_auth_observe_patch.py\`, extracting the exact newly added source blocks from the committed patch and compiling under mocked CCB/BTM types and \`LOG_INFO\` with \`g++ -std=c++17 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined\`. Run source patch test with the flag **off and on**.

\`\`\`text
1/1 PASS (feature off; no observer logging)
16/16 PASS (feature on; mock types, observer only)
\`\`\`

On-mode assertions cover incoming Control/Interrupt PSM, outbound request ignored in BTM, unrelated PSM ignored, live Control/Interrupt callback results, unrelated RCB, null RCB, and emitted log content. Mock callback result 42 is synthetic and not asserted to be a HCI error code.

The **two original context hunks were independently matched against the exact GitHub upstream file contents**. \`git apply --check\` using a complete pinned source checkout and full native Android compilation were **not run**; the host test compiles only the added observer fragments against fake types, not native Fluoride.

The test was added to \`run_cpp_host_tests.sh\`. To rerun:
\`\`\`bash
python3 experiments/m3-ds3-cable-session/test_h618_btm_auth_observe_patch.py
\`\`\`

## Still unproven / prioritization

- Both observability hooks are after the incoming HID channel access request. If an HCI authentication is initiated earlier by bonding or another security path, these logs may not cover its cause. Their lack of output must **not** be interpreted as evidence that HID auth was not attempted.
- BTM \`btm_sec_auth_complete\` has a peer security record and HCI handle but **not the original PSM**. Correlating it to a specific inbound HID CCB by address alone or handle alone risks stale/reuse errors. A future observer would need independently safe ACL generation and bounded lifetime, not a fake global \`last_ds3\`.
- The observation-only callback may log BTM_SUCCESS after stock normalization of BTM_SUCCESS_NO_SECURITY; exact predecessor code determines meaning. No authentication success is proven.
- USB \`0xF5\` enrollment writes the host address into DS3 but does not cryptographically prove that a later radio MAC belongs to the USB-attended controller. A limited compatibility exception remains a **bounded spoofing risk** requiring explicit Owner consent, never a blanket HID downgrade.
- A future **real** adapter, if justified, needs scoped PSM+direction+session state, protected Native-to-Java admission response, bounded HID descriptor and input parsing, and recovery. The already missing full matching BSP on owner host makes deployment **NO_GO**. PR #50 remains reverse-engineering archive and PR #51 remains separate build source work.

**Decision:** source-anchored auth trace + observation-only H618 patch and host tests PASS; genuine DS3 wireless admission remains **NOT IMPLEMENTED / NO_GO**. No runtime M3 operations, no APK, firmware, privileged injection, Bluetooth service restart, production writes, or PR merge authorized.
