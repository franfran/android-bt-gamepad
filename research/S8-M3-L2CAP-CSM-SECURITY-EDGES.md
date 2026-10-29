# S8: Actual M3 L2CAP channel state machine enters BTM security (offline verified)

**Input:** Owner-provided original ARM32 `libbluetooth.so`, SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`; embedded `.gnu_debugdata` recovered and matched to live machine-code addresses. All addresses are **ELF VMAs**, not runtime offsets. **No device or service changes.**

## New static proof — missing edge between L2CAP and security BTM

The original ELF embedded mini-debug names:
- `l2c_csm_execute(t_l2c_ccb*,tL2CEVT,void*)` at Thumb entry **0x2860b0**, size 14672.
- `btm_sec_l2cap_access_req(RawAddress const&,unsigned short,bool,callback,void*)` at **0x258e68**, size 504.
- `btm_sec_l2cap_access_req_by_requirement(RawAddress const&,unsigned short,bool,callback,void*)` at **0x258734**, size 1564.
- `btm_sec_execute_procedure(tBTM_SEC_DEV_REC*)` at **0x257c04**.

Disassembling **actual original binary**, direct Thumb BL instructions establish:

| Caller | Exact callsite ELF VMA | Target |
|---|---|---|
| `l2c_csm_execute` | **0x286ea8** | `btm_sec_l2cap_access_req` 0x258e68 |
| same | **0x288b20** | same |
| same | **0x2897b4** | same |
| same | **0x289808** | same |
| same | **0x2898aa** | same |
| `btm_sec_l2cap_access_req` | **0x258ffe** | `btm_sec_l2cap_access_req_by_requirement` 0x258734 |
| `btm_sec_l2cap_access_req_by_requirement` | **0x258b5a** | `btm_sec_execute_procedure` 0x257c04 |

This fills the major static gap in prior PRs: the channel-state-machine handler itself explicitly invokes the BTM service-security request wrapper, which in turn invokes the requirement-based security function. It is **not simply a similarly named function or AOSP expectation**.

## How this connects to the earlier validated evidence

- PR #28 proves that HID Control PSM 0x11 and Interrupt PSM 0x13 register the same real `tL2CAP_APPL_INFO` callback table (first entry `hidh_l2cif_connect_ind`).
- PR #29 proves `0x36` gets from `hidh_conn_reg` through `L2CA_Register2` as the seventh argument to `BTM_SetSecurityLevel`.
- **This PR #30** proves `l2c_csm_execute` has concrete security request callsites; `btm_sec_l2cap_access_req` delegates to `by_requirement`, which has a verified call to `btm_sec_execute_procedure`.
- Historic original HCI capture records DS3 HID Control PSM 0x11 request before host HCI Authentication Requested and HCI status **0x22** timeout.

## Important limits and next decision gate

**Proven:** Static M3 call relationships in the native code image.

**Not proven:** Which of the five `l2c_csm_execute` callsites actually executes on the recorded *incoming* DS3 PSM 0x11 request; which event/state/branch predicates select that callsite; whether the eventual `btm_sec_execute_procedure` triggers the observed HCI 0x0411 command in that attempt; whether GD shim path is engaged. The direct calls exist even if different conditions are active.

**Do not patch `0x36` globally, fake link keys, infer an authenticated connection from a host PIN reply, or attempt device injection.** The next offline step is to annotate per-callsite state conditions and the security requirement bits used in `btm_sec_l2cap_access_req` for incoming PSM 0x11, using the original ELF and annotated AOSP code as *separate* evidence.

## Reproduce offline with exact original ELF

```sh
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x2860b0 --stop-address=0x289bb0 libbluetooth.so | grep '0x258e68'
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x258e68 --stop-address=0x25905c libbluetooth.so | grep '0x258734'
llvm-objdump -d --triple=thumbv7-linux-androideabi --start-address=0x258734 --stop-address=0x258d50 libbluetooth.so | grep '0x257c04'
```

The original vendor ELF remains private and **was not added to GitHub**. S7 C4C-3 live-injection NO-GO remains in effect.
