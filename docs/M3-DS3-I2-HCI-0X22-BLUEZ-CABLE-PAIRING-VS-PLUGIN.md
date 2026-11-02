# PR #52 — 0x22 LMP timeout, four HCI windows, BlueZ cable pairing, and M3 plugin feasibility

**Date:** 2026-11-02. **Scope:** iMETBOX M3 **onboard** Bluetooth and possible removable **software plugin**. **No USB Bluetooth dongle, second controller, BSP build, OS/library/APK replacement, HCI runtime commands, authentication changes or injection.** Research only; PR #52 Draft.

## Corrected protocol meaning — two distinct HCI error codes

The **event** was **HCI Authentication Complete (event 0x06)** carrying the **status** \`0x22\`, which means **LMP Response Timeout** for BR/EDR. This is **not** the distinct HCI error status \`0x05 = Authentication Failure\`. It does **not** prove a bad PIN or an incorrect LinkKey, even though the authentication procedure failed to complete.

Canonical status definitions: [Bluetooth SIG Controller Error Codes](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core_v6.3/out/en/architecture%2C-change-history%2C-and-conventions/controller-error-codes.html). User's terminology correction: [PR #52 comment](https://github.com/franfran/android-bt-gamepad/pull/52#issuecomment-6581148606), commit \`d46dcb79aeef54b3181f0bf35a1d4a338fba2f9a\`.

## Stronger *within-HCI* evidence: four intact DS3 pairing windows

Read the [previously verified H4 btsnoop audit](M3-DS3-I2-UPLOADED-HCI-FOUR-ATTEMPTS.md), not just older unsynchronized historical anecdotes. The Owner's previously uploaded main btsnoop contains **four distinct complete captured HCI sessions** (Oct 29–30 UTC). For each:

1. HCI Connection Complete event \`0x03\` success
2. Host **Authentication Requested** command \`0x0411\`
3. Controller **Link Key Request** \`0x17\` followed by host **Link Key Request Negative Reply** \`0x040C\` (no known link key)
4. Controller **PIN Code Request** event \`0x16\`
5. **No host HCI PIN Code Request Reply \`0x040D\` or Negative Reply \`0x040E\` is present in the captured HCI window**
6. \`Authentication Complete\` event \`0x06\` status \`0x22\` after **30.061, 30.061, 30.067 and 30.063 seconds** from PIN request; disconnect reason \`0x22\`.

Those are **sanitized metadata**, not new captures. A separately captured Oct 31 Android diagnostic shows \`pinRequestCallback\` for a device named PlayStation 3 Controller, \`BluetoothPairingRequest: onPair: null\`, and bonding collapsing to NONE in ~30 s. **Do not cross-correlate Oct 31 logcat with the Oct 29–30 HCI sessions as if same-attempt synchronous.** Earlier historic reports of a host PIN reply are from distinct observations; do not silently merge them with these four no-reply HCI sessions.

**High-priority hypothesis:** Android pairing UI/dispatch failing to return a valid local PIN (or lack of the required cable-pairing policy) may be the immediate cause of the unresolved HCI state. **Not yet established:** which exact input the genuine DS3 expects, whether a normal PIN response is protocol-correct, whether an OTA response was received, whether authenticated/encrypted HID is supported, whether timing and local HCI capture are exhaustive on all transports, or whether the next native/Java/UHID gate would pass.

## Pinned Android 12 source: *a narrow software companion API does exist*

Immutable H618 reference source: \`BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d\` (matching family, **not** byte-identical OEM ABI).

- [\`BondStateMachine.java:257–285\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/btservice/BondStateMachine.java#L257-L285) dispatches \`PIN_REQUEST\` to display PIN variant 0 or 16-digit variant 7 (except keyboard handling).
- [\`BondStateMachine.java:364–377\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/btservice/BondStateMachine.java#L364-L377) emits **\`BluetoothDevice.ACTION_PAIRING_REQUEST\`** as an ordered foreground broadcast with a \`BLUETOOTH_CONNECT\` receiver requirement. A suitably permitted external APK **may** receive it, conditional on actual OEM routing/Android component restrictions.
- [\`BluetoothDevice.java:1858–1877\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/frameworks/base/core/java/android/bluetooth/BluetoothDevice.java#L1858-L1877) has **public \`setPin(byte[])\`**, forwarded to the Bluetooth Binder. [\`AdapterService.java:1919–1942\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/btservice/AdapterService.java#L1919-L1942) enforces Bluetooth connect caller/active user and bonding/bonded state before \`pinReplyNative\`. This is a **supported pairing reply path**, not a general native stack hook.
- [\`btif_dm_pin_reply\`: L2100–2118](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_dm.cc#L2100-L2118) routes BR/EDR through \`BTA_DmPinReply\`. [\`BTM_PINCodeReply\`: L614–711](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/btm/btm_sec.cc#L614-L711) checks current pairing state, peer, record, *nonempty* PIN length <=16; then (in the applicable branch) emits the **actual HCI PIN Code Request Reply**. A UI method return value is **not** proof a command reached HCI or the remote controller.
- Prior [PR #50 exact OEM TvSettings evidence](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-PAIRING-IMPLEMENTATION-PLAN.md) records a \`BluetoothPairingRequest.onPair(variant,null)\` branch; don't assume the same source line occurred in the earlier four timestamped HCI sessions.

**Important candidate classification:** A permission-correct, removable **pairing-request receiver/companion APK** is **CONDITIONAL** as a way to address **only the first UI/PIN request handoff**. This is **NOT** proof the PIN required by DS3 exists/is suitable, that the broadcast reaches a third-party APK in the OEM image, or that any plugin can authenticate a cable-paired unbonded DS3. Do **not** generate, submit, brute-force or hardcode a PIN now. No live permission/receivers/pairing tests authorized.

## The decisive DS3 nuance: working BlueZ plugin is *cable pairing*, NOT a generic PIN filler

Reference: public BlueZ [tag 5.83 \`plugins/sixaxis.c\`](https://github.com/bluez/bluez/blob/5.83/plugins/sixaxis.c), [\`profiles/input/device.c\`](https://github.com/bluez/bluez/blob/5.83/profiles/input/device.c), [\`profiles/input/server.c\`](https://github.com/bluez/bluez/blob/5.83/profiles/input/server.c). BlueZ is **not** running on M3 Android and its plugin ABI does not exist in Android Fluoride by implication.

- [\`sixaxis.c:267–306\`](https://github.com/bluez/bluez/blob/5.83/plugins/sixaxis.c#L267-L306) requests **user cable authorization**, sets USB controller's intended central/host address, stores HID SDP and marks device **cable paired**. [\`sixaxis.c:555–556\`](https://github.com/bluez/bluez/blob/5.83/plugins/sixaxis.c#L555-L556) invokes **\`BLUETOOTH_PLUGIN_DEFINE(sixaxis,...)\`**, a *real BlueZ plugin registration interface*.
- [\`device.c:1088–1105\`](https://github.com/bluez/bluez/blob/5.83/profiles/input/device.c#L1088-L1105) **specifically exempts** previously cable-paired devices from ordinary Classic bonded-only admission and encrypted-link enforcement; a cable-paired DS3 does not necessarily have a conventional LinkKey.
- [\`server.c:269–311\`](https://github.com/bluez/bluez/blob/5.83/profiles/input/server.c#L269-L311) sets **\`BT_IO_SEC_LOW\`** on its HID listening sockets while cable-pairing support is active, then identifies/restricts devices separately. This is a **different security architecture**, not a PIN-response handler. **Do not copy this adapter/listener-wide security lowering into M3**, whose existing Fluoride registers HID Control/Interrupt PSMs with authentication and encryption. It risks exposing non-DS3 peers. BlueZ behavior is proof of the concept, NOT safe equivalence to Android or cryptographic authentication.
- Android pinned [\`hidh_conn.cc:95–116\`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/hid/hidh_conn.cc#L95-L116) registers *existing* Classic HID PSM 0x11/0x13 with \`BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT\`, before the Java [\`HidHostService.okToConnect\` bond gate](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/packages/apps/Bluetooth/src/com/android/bluetooth/hid/HidHostService.java#L892-L917).

### What this means for the *plugin feasibility question*

| Independent candidate | What its API can plausibly do | What is still missing | Decision |
| --- | --- | --- | --- |
| **External Android pairing receiver + \`setPin(byte[])\`** | Potentially answer the *first* HCI PIN request if an actual protocol-correct PIN and permissions exist | Cannot reconfigure native per-DS3 L2CAP security, bypass OEM Java bond check safely, or complete kernel UHID SET_REPORT through this API | **CONDITIONAL first-gate only**; **not** whole DS3 plugin |
| **Actual BlueZ Sixaxis plugin** | Has explicit plugin ABI, USB authorization, paired-device state and HID security handling in BlueZ | No Android Fluoride equivalent confirmed; direct server-wide low security unacceptable | **Not portable as a drop-in plugin** |
| **OEM-specific private plugin / IPC** | Unknown until raw original OEM loader, vendor HAL, JNI and APK ABI inspection | Must prove legitimate scoped BTM/HID/Java/UHID authority and lifecycle | **UNRESOLVED**, do not declare impossible |
| **Only changing HCI 0x22 label or inserting generic PIN** | Corrects diagnosis or possibly one UI symptom | Does not prove real link negotiation, cable pairing or Java/UHID path | **NO evidence of wireless fix** |

Thus **0x22 clarification is a meaningful diagnostic correction**, and four full HCI attempts support "missing HCI PIN reply" as a first observable blockage, but *neither* proves wrong PIN nor creates an external HID plugin ABI. Do **not** silently redirect #52 to source modifications or a USB dongle.

## New safe host-only regression / capture contract

The [strict sanitized HCI classifier](../experiments/m3-ds3-compat-adapter/classify_sanitized_hci_timeout.py) accepts ONLY per-attempt ordered **relative milliseconds**, allowlisted event names/statuses, and a mandatory explicit \`capture_complete\` boolean. It refuses MACs, PINs, LinkKeys, absolute timestamps, raw packets, logs or unexpected fields. It distinguishes 0x22 versus 0x05, tracks whether a PIN HCI reply command was actually present, and rejects incomplete capture or interleaved/late replies from confident absence claims. Synthetic tests include the four **previously documented** 30.061/30.061/30.067/30.063-second intervals; no raw HCI capture is committed. No Android device or Bluetooth stack is accessed. \`capture_complete=true\` is an *operator assertion*, not independently verified by a model; "no PIN reply" only means **none observed in this selected capture window**.

Reproduce:

\`\`\`bash
python3 -m unittest discover -s experiments/m3-ds3-compat-adapter \
  -p test_classify_sanitized_hci_timeout.py -v
\`\`\`

The preexisting [Legacy Auth Trace CI](../.github/workflows/retrobox-legacy-auth-trace.yml) was extended to invoke these tests. **[Actual GitHub Actions run 41475207689](https://github.com/franfran/android-bt-gamepad/actions/runs/41475207689) completed SUCCESS** at documentation commit `796075fb9b`: the earlier observer regression ran **13 tests / OK**, followed by **17 new sanitized-HCI synthetic tests / OK**. A previous [run 41475062170](https://github.com/franfran/android-bt-gamepad/actions/runs/41475062170) also reported the same 13 + 17 tests successfully. These are host-only test validations, not raw HCI analysis or a real device test.

## Remaining acceptance and safety decisions

**P1/P2 unchanged:** verify true M3 OEM plugin loader/extension ABI (already-collected 2024 original ELF, JNI, APK + exact SHA checks), not hypothetical standard Fluoride APIs. **P3 refined:** even a permission-correct companion APK handling ACTION_PAIRING_REQUEST is a *narrow PIN reply hook* — test its authority coverage on paper, fail full plugin GO unless it legitimately addresses native HID security, Java bond and UHID lifecycles. **P4:** if no supported OEM extension covers all independent gates, output **NO_GO for removable plugin on this OEM version** with evidence limits; do not redefine plugin to mean remote process injection, library replacement or global security bypass.

**No M3 operation performed**, no new PIN submission, no security state changes, no proof of normal classic pairing and no production plugin written. Raw btsnoop and identifying logs remain private. PR #50/#51 untouched; PR #52 Draft.
