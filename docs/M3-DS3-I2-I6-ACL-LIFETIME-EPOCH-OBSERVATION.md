# I2/I6 — ACL lifetime epoch + HID PSM: disabled H618 observation patch

**Workstream:** Draft PR #52 (`research/m3-ds3-compat-adapter`). **Reference:** `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. **Not** an Android build, identity proof, security exception, M3 test or wireless gamepad fix.

## Verified source-level lifecycle

- [`l2c_link_hci_conn_comp`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_link.cc#L138-L190) receives BR/EDR HCI connection complete, sets the LCB handle and transitions the LCB to `LST_CONNECTED` on `HCI_SUCCESS`.
- [`l2c_link_hci_disc_comp`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_link.cc#L337-L439) may **retain the same LCB** for pending reconnect, instead of immediately freeing its storage. The code explicitly discusses pending-CCB races.
- [`l2cu_allocate_lcb`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_utils.cc#L56-L90) reuses entries in a fixed LCB pool and initializes their state/invalid handle; [`l2cu_release_lcb`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_utils.cc#L149-L189) also releases LCB resources on other paths. Therefore pointer identity and HCI handle alone are **NOT stable connection identities**.
- [Incoming Classic HID security request](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_csm.cc#L295-L309) has the exact PSM before `btm_sec_l2cap_access_req()`; [`l2c_link_sec_comp2`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/stack/l2cap/l2c_link.cc#L272-L325) checks a currently live CCB pointer before routing the BTM result. Neither existing callback embeds a separately minted immutable ACL generation.

## New source patch (disabled by default)

`experiments/m3-ds3-cable-session/h618_acl_epoch_observe_disabled.patch`, feature guard **`RETROBOX_DS3_ACL_EPOCH_OBSERVE`** (unset):

| Pinned H618 path | Added passive observation |
|---|---|
| `stack/l2cap/retrobox_acl_epoch_observer.h` | New fixed-capacity C++17 debug-only `AclEpochObserver`, no peer addresses, keys, PIN, bond mutation, or authorization method |
| `stack/l2cap/l2c_link.cc` | Mint new **observation generation** after HCI connection success; retire on disconnect; annotate matching HID PSM 0x11/0x13 BTM callback status with current observed generation; expose read-only epoch accessor |
| `stack/l2cap/l2c_csm.cc` | Annotate inbound HID Control/Interrupt security request with current observation generation before calling unchanged BTM security API |
| `stack/l2cap/l2c_utils.cc` | Retire observer entry on final LCB release as well, covering cleanup outside standard HCI disconnect-complete path |

**No original source lines are removed**, and every addition to original source files is under the unset research guard. Existing HID registration security flags, authentication outcome, CCB reference, BTM callback, Java gate, HCI command and normal bonded HID paths remain unchanged.

**Observation table details:** fixed 32-slot **research** capacity (NOT a verified production constant); each successful `Connected(handle, LCB)` mints a new monotonic 64-bit generation and retires entries sharing a handle or LCB slot. Exhaustion returns no ticket, not a guessed one. `Retire(ticket)` refuses stale generations; `Clear()` preserves generation within the same process. No MAC, PIN, LinkKey or descriptor bytes are serialized or logged. Log events contain PSM/status/epoch only.

## Host tests and evidence

Committed:
- `experiments/m3-ds3-cable-session/acl_epoch_observer.h`
- `experiments/m3-ds3-cable-session/test_acl_epoch_observer.cc`
- `experiments/m3-ds3-cable-session/verify_h618_acl_epoch_observer.py`
- Updated `experiments/m3-ds3-cable-session/run_cpp_host_tests.sh`

**Actually run in a local isolated Linux host environment:**

```text
g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  test_acl_epoch_observer.cc -o test_acl && ./test_acl
14/14 PASS (host-only ACL epoch observer)

g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  test_acl_epoch_observer.cc -o test_acl_san
ASAN_OPTIONS=detect_leaks=1 ./test_acl_san
14/14 PASS (host-only ACL epoch observer)
```

Tests cover handle reuse, same LCB/new handle, same handle/same LCB reconnect, stale retirement, cross-session isolation, invalid handle and null identity, bounded table refusal, clear/reopen and independent concurrent observed sessions. These are **host model tests**, not proof that the H618 integration compiles.

All **9 change hunks across 3 existing H618 files** were checked against the corresponding exact pinned upstream lines, including verified original/new line counts; the fourth patch section creates the new header and was checked byte-for-byte against the committed host header. No original lines deleted. This is a source-content audit, **not** a complete `git apply --check` or full Android build.

The reproducible script `verify_h618_acl_epoch_observer.py` performs local patch/header guard checks and builds the host suite with and without sanitizers. With an **actual exact pinned full BSP checkout**, it optionally calls `git apply --check` (never `git apply`):

```bash
cd experiments/m3-ds3-cable-session
python3 verify_h618_acl_epoch_observer.py
# Optional only if full BSP is available and HEAD exactly equals pinned SHA:
python3 verify_h618_acl_epoch_observer.py --source-tree /path/to/BPI-H618-Android12
```

The exact repository Python wrapper and the optional full-BSP application check **have not been run in this turn**. Host compiler tests were run directly; H618 original hunk matching and header consistency were verified through pinned GitHub source retrieval.

## Important security / instrumentation limitations

1. **Observation epoch is not a cryptographic peer identity or authorization grant.** The `LCB` address is an in-process slot identifier. MAC and VID/PID remain spoofable; the owner-approved USB-once workflow does not grant permission to relax runtime Bluetooth security.
2. The event logs look up the **currently live epoch**, not an immutable epoch saved in the original BTM→L2CAP callback. After an extremely fast disconnect/reconnect, a stale BTM callback could coincide with a reused CCB pointer, and the observer could **mislabel** its generation. This is why the observer is **never used to decide authentication or `UHID_CREATE`**. A production decision would require event-bound correlation minted before asynchronous BTM work and carried through the callback.
3. HCI Authentication Complete status `0x22` is known from prior owner capture, but **this observer does not directly hook `btm_sec_auth_complete`**; it monitors channel-level security requests and callbacks. It must not be claimed to explain every HCI bonding flow. A source-level authentication bypass is not justified.
4. A stale HCI disconnect completion with an identical recycled LCB/handle may cause the read-only observer to retire the *current* debug ticket; the status cannot prove old/new session by handle alone. This is an **observation accuracy limitation**, not a safe authorization design.
5. The patch is not enabled in any build and **no target-side run, libbluetooth.so build or ABI check has occurred**. Per `AGENTS.md` and `docs/SAFETY.md`, do not install/inject/test this in the real Bluetooth process without separate explicit approval and independent recovery. PR #51 full-BSP availability is still NO_GO.

## Next actual milestone

Before any security decision: design immutable request-bound token transport across BTM/L2CAP; trace ACL HCI handle lifecycle against the pending CCB and reconnect races; verify how an owner-attended USB enrollment record could be bound to the specific runtime session without claiming cryptographic identity; preserve Java `BOND_BONDED` and HID report safety. This remains a **review-only architecture decision**, not consent to weaken HID security.

**Decision:** offline C++ observer + pinned source patch audit PASS; full Android integration, DS3 wireless support and deployment NO_GO.
