# I2/I6 — DS3 legacy Bluetooth: LinkKey, PIN and HCI authentication decision

**PR:** #52, research/m3-ds3-compat-adapter (Draft). **Pinned reference:** BPI-SINOVOIP/BPI-H618-Android12 @ 250eabfc529518b7f26432663ed0a867ab2f625d. **Device deployment:** NO_GO. PR #50 and #51 remain independent.

## Evidence and root-cause limit

Existing M3 evidence: DS3 USB gameplay through RetroArch works, USB sixpair wrote the intended Bluetooth host address, yet the wireless attempt encountered a PIN request and HCI 0x22 timeout, with Android bonding returning to BOND_NONE.

HCI 0x22 is **LMP Response Timeout**, not a definitive "wrong PIN" result. The Bluetooth SIG Core specification describes it as an LMP/LL response timeout; the legacy BR/EDR context concerns LMP. The source alone cannot establish whether the cause is the Android PIN handoff, remote firmware, controller interoperability, absent on-air reply, or some other prerequisite. Avoid treating this as a kernel UHID failure.

## Exact pinned-source branches

1. **Link-key lookup:** [btm_sec_link_key_request, btm_sec.cc around L3924–3954](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L3924-L3954) sends a known LinkKey or issues the standard Link Key Request Negative Reply when unknown; USB host-address enrollment does not create a LinkKey.
2. **PIN request:** [btm_sec_pin_code_request, btm_sec.cc around L4071–4200](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L4071-L4200) handles a fixed PIN, a prefilled PIN, rejection, or a WAIT_LOCAL_PIN callback; the latter may first request the remote name. An HCI PIN request does not prove a Java UI callback was delivered.
3. **BTIF PIN handoff:** [btif_dm_pin_req_evt, btif_dm.cc around L689–765](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_dm.cc#L689-L765) allows narrow automatic PIN paths for certain device classes and locally initiated pairing, otherwise calls invoke_pin_request_cb. The new trace logs UI handoff but does not log all auto-pair returns. Absence of handoff is inconclusive.
4. **Local PIN reply validation:** [BTM_PINCodeReply, btm_sec.cc around L614–710](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L614-L710) validates pairing state, peer, device record and PIN length before accepting the local response. That does NOT confirm the remote controller accepted the PIN; HCI pin-code command may still be deferred.
5. **Actual HCI authentication:** [btm_sec_start_authentication, btm_sec.cc L4391–4394](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L4391-L4394) issues btsnd_hcic_auth_request(hci_handle). [btm_sec_auth_complete, L3043–3170](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L3043-L3170) consumes the HCI status. The explicitly guarded retry in [btm_sec_auth_retry, L3009–3041](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L3009-L3041) concerns missing key for SM4 devices, not timeout 0x22.

## New disabled-by-default source diagnostic

File: experiments/m3-ds3-cable-session/h618_legacy_auth_decision_trace_disabled.patch

Compile flag: **RETROBOX_DS3_LEGACY_AUTH_TRACE** (unset). Changes ONLY stack/btm/btm_sec.cc and btif/src/btif_dm.cc using preexisting BTM_TRACE_EVENT / BTIF_TRACE_EVENT. Ten diff hunks total: nine BTM and one BTIF. Captures:

- Known/unknown LinkKey request; LinkKey notification type only
- PIN request state and boolean route prerequisites; fixed, preset, upper callback or name-pending branches
- The local BTM PIN reply result **after peer/state/PIN-length validation**
- Upper BTIF forwarding to Java PIN callback
- Raw HCI Authentication Complete status and BTM state

No existing security statements are removed; no PIN value, LinkKey bytes, Bluetooth address, HCI packet contents, or fake success is introduced. Raw Android stock logging may still include private identifiers: never commit unredacted captures.

The final ten source hunks were independently checked against the exact pinned H618 GitHub source with old/new counts and cumulative offsets. Full Android BSP git apply --check, native ARM32 compilation and real device logging have NOT been performed.

## Offline analyzer

- experiments/m3-ds3-cable-session/analyze_legacy_auth_trace.py
- experiments/m3-ds3-cable-session/test_analyze_legacy_auth_trace.py
- experiments/m3-ds3-cable-session/verify_h618_legacy_auth_trace_patch.py
- run_cpp_host_tests.sh invokes the verifier

The analyzer ignores non-observer text, emits only whitelisted summary metadata, and refuses causal analysis when multiple PIN requests or HCI completions are interleaved without peer/session IDs.

**13/13 synthetic scenarios PASS** in a local equivalent interpreter re-execution of the classifier logic. The exact committed Python scripts and full runner have NOT been executed in this increment. Do not report the equivalent interpreter check as a live capture or Android test.

Reproduce locally on the repo checkout:

    python3 experiments/m3-ds3-cable-session/verify_h618_legacy_auth_trace_patch.py

If an exact pinned full BSP exists, the verifier also accepts --source-tree and runs only git apply --check. It never applies patches.

## Conservative decision table

| Future sanitized single-attempt evidence | Interpretation | Forbidden leap |
|---|---|---|
| LinkKey known=0, then PIN request | Standard legacy pairing continues without stored key | Claim USB pairing failed or invent a LinkKey |
| UI callback/name pending but no valid BTM PIN reply | PIN handoff or name-resolution path warrants investigation | Call it definitely wrong PIN or definitely Android UI failure |
| Valid local BTM PIN reply then HCI 0x22 | Link-layer authentication still failed after valid local submission | Declare that HCI PIN was sent or accepted on air without more evidence |
| HCI status 0x00 then Java BOND_NONE | Investigate state/persistence independently | Forge BOND_BONDED or grant UHID |
| Multiple attempts without immutable session IDs | Ambiguous; separate attempts before analysis | Attribute another device's result to DS3 |

**Next engineering priority:** matching public/OEM BSP build readiness (PR #51) and a proven one-shot, supervised, independently recoverable diagnostic plan if separately approved. Do NOT enable the research flag, alter security, push binaries, restart Bluetooth, capture unredacted keys or try live pairing yet.

**Decision:** source-first PIN/LinkKey/HCI decision branches characterized; passive research trace prepared; production DS3 wireless authentication compatibility remains NO_GO.
