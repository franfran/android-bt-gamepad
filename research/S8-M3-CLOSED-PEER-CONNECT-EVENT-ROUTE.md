# S8 — Actual M3 CLOSED-state peer L2CAP CONNECT_REQ → Classic BTM security route

**Date:** 2026-10-29. **Input:** user-provided original M3 Android 12 ARM32 `libbluetooth.so`, SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`, inspected locally read-only. **Exact ELF VMA, not runtime ASLR address**. The original ELF is NOT committed to GitHub.

## Conclusive NEW static path (previously missing state/event dispatch)

M3's `l2c_csm_execute(t_l2c_ccb*,tL2CEVT,void*)` recovers channel state from `[r10+4]`, then selects nine state cases using the **real** Thumb TBH at `0x2861ce`. Its index-0 halfword at `0x2861d2` leads to **0x2861e4**. AOSP L2CAP enumeration (also matching the M3 nine states) names state 0 `CST_CLOSED`.

From state-0 handling, one verified conditional predecessor at **`0x286242: beq.w 0x286cfe`** reaches an **actual EVENT dispatch**, separate from the diagnostic event-name lookup rejected in PR #34:

- `0x286cfe: cmp.w r8,#0x2d` (checks event 0..45)
- `0x286d0a: tbh [pc,r8,lsl #1]` (real control-flow branch)
- `0x286d0e + 10*2` contains halfword **`0x0cb1`**
- Thumb TBH destination = `0x286d0e + 2*(0x0cb1) = 0x288670`.
- AOSP `l2c_int.h` identifies **event 10 as `L2CEVT_L2CAP_CONNECT_REQ`** (peer-initiated L2CAP connection request). This enum name comes from AOSP cross-check, not an executed DS3 trace. Relevant AOSP source: https://android.googlesource.com/platform/system/bt/+/23a92b652dcc7f830fb1c12d98d545e4222df40d/stack/l2cap/l2c_int.h

Now connected to earlier real-M3-ELF dataflow:

```text
l2c_csm_execute()
  CCB state [r10+4] == 0
    -> state TBH 0x2861ce, index 0 -> 0x2861e4
       -> branch at 0x286242 (CONDITIONAL: beq) to 0x286cfe
          -> event TBH 0x286d0a, index 10 -> 0x288670
             -> inspect connection record byte +0xC9 (0x28867e)
                ==2: LE l2ble_sec_access_req (0x2886a2)
                !=2: Classic branch (0x288684 -> 0x289772)
                     BTM_SetLinkPolicyActiveMode (0x289774)
                     PSM from channel service record
                     is_originator=0
                     btm_sec_l2cap_access_req (0x2897b4)
                       -> by_requirement (0x258ffe)
                          -> btm_sec_execute_procedure (0x258b5a)
                     result STARTED (1) -> l2cu_send_peer_connect_rsp
                       result PENDING (1) (0x2897c4)
```

The security route therefore has **static event provenance**, finally matching the prior Stage3C HCI capture's observation of an incoming DS3 HID Control PSM 0x11 connection request before local HCI Authentication Requested.

## Precisely what this proves / what it does NOT

**Proven from original ELF bytes:** both state/event TBH switches and state-0/event-10 destination; conditional predecessor; LE-versus-Classic function split; PSM and remote device context; incoming security BTM callsite; pending peer response on BTM CMD_STARTED. Source enum maps event 10 to peer CONNECT_REQ. This is meaningfully stronger than the previous isolated-callsite inventory.

**Not proven:** The predicate controlling `0x286242` was satisfied for the recorded DS3 attempt (state0 event dispatch has more branches); that the M3 runtime used this static path; which precise BTM security branch generated the captured HCI `0x0411` authentication request; whether DS3/host/controller LMP incompatibility versus policy caused `0x22`. Even correctly identifying this path does not justify disabling authentication on all HID devices or assuming unauthenticated HID is acceptable.

## Practical next research / future experiment boundary

Our research should now move past re-identifying the L2CAP service registration and event mapping. The next blocker is **the specific Classic security decision/action**, and proof that a trusted USB-enrolled DS3 can establish HID transport safely on the actual M3 Bluetooth controller. Compare M3 `btm_sec_l2cap_access_req` / `btm_sec_execute_procedure` branches with Android 12 security manager source and inspect host HCI auth request handling; a host controller command accepted is not proof of remote authentication. Document an owner-authorized, reversible deployment/recovery design before any real Bluetooth changes.

## Reproduce without uploading original binary

```sh
python3 experiments/s8-peer-event/verify_route.py /private/local/libbluetooth.so
```

The verifier refuses wrong ELF fingerprint, incorrect opcode bytes, altered TBH table entries or invalid ELF mapping. CI exercises synthetic ELF fixtures **only**; a passing synthetic test does not substitute for owner hardware testing. The original matching binary was separately checked in the offline analysis environment.

**Decision:** C4C-3 injection remains NO-GO, no Android Bluetooth service modification, no global security relaxation, no counterfeit Link Keys.
