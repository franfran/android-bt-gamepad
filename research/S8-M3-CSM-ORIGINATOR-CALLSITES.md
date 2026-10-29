# S8 — Classify M3 L2CAP CSM security calls by originator flag

**Source:** owner-uploaded ARM32 M3 `libbluetooth.so`, SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`. Original ELF inspected privately, not committed. Exact ELF virtual addresses below are not live ASLR locations.

The archived HCI trace already establishes DS3 **initiates incoming** HID Control PSM `0x11` request, followed by host HCI Authentication Requested and status `0x22`. Draft PR #30 confirmed **five** `l2c_csm_execute` → `btm_sec_l2cap_access_req` direct calls. This analysis inspects the AAPCS argument register **r2** immediately before each call, identifying its boolean `is_originator` parameter.

| Security call at | Set r2 at | Value | Role |
| --- | --- | --- | --- |
| `0x286ea8` | `0x286ea2` | `movs r2,#0` | Non-originator / incoming-side candidate |
| `0x288b20` | `0x288b1e` | `movs r2,#1` | Originator / outgoing-side |
| `0x2897b4` | `0x2897ae` | `movs r2,#0` | Non-originator / incoming-side candidate |
| `0x289808` | `0x289802` | `movs r2,#1` | Originator / outgoing-side |
| `0x2898aa` | `0x2898a8` | `movs r2,#1` | Originator / outgoing-side |

**New result:** Among five security-access callsites, only `0x286ea8` and `0x2897b4` are incoming-side candidates from these local arguments. This narrows follow-up control-flow recovery; it does **not** prove the actual DS3 HID PSM `0x11` path reaches either one. In particular, both need their entry branch predicates, channel state, and event dispatch resolved. The PSM passed via `r1` comes from the channel service record and must be independently verified per branch.

**Important distinction:** The observed host `Authentication Requested` command is a later lower-stack operation; even if an incoming candidate is selected, `0x22` does not uniquely identify which peer/device/policy fault caused timeout. The firmware/security exception and safe runtime intervention remain unproven.

### Reproducible source audit

```sh
llvm-objdump -d --triple=thumbv7-linux-androideabi \
  --start-address=0x286e90 --stop-address=0x286eb8 libbluetooth.so
llvm-objdump -d --triple=thumbv7-linux-androideabi \
  --start-address=0x288b14 --stop-address=0x288b24 libbluetooth.so
llvm-objdump -d --triple=thumbv7-linux-androideabi \
  --start-address=0x289796 --stop-address=0x2898b4 libbluetooth.so
```

Run the read-only `experiments/s8-l2cap-direction/audit_originator.py` over a combined disassembly text; the CI tests use synthetic excerpts and deliberately preserve `exact_ds3_hid_psm_path=UNVERIFIED`.

### Next meaningful experiment

Reconstruct the **event/state jump-table entries and predecessor branches** leading to `0x286ea8` and `0x2897b4`, plus track the channel record's PSM through `r1`. That is the remaining static evidence needed before considering any scoped DS3 compatibility policy. No device changes, software injection, global `0x36` change, PIN/key forgery, or Bluetooth restart. S7 C4C-3 live gate stays **NO_GO**.
