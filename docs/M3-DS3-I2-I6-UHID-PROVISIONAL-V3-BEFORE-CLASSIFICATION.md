# I2/I6 — UHID v3: provisional fd before Native peer classification

**Repository:** `franfran/android-bt-gamepad`, Draft PR #52. **Pinned public source:** `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`. **Target:** iMETBOX M3 Android 12 ARM32. **Current deployment gate: NO_GO.**

## Exact source finding: fd open comes before safe peer classification

[`bta_hh_co_open`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L317-L390) receives **HID handle/subclass/attr-mask/app-id** but not an immutable ACL request ticket or trustworthy DS3 identity. It opens `/dev/uhid` in **two separate paths** (reconnect and new slot) and creates its polling thread before returning. Later [`BTA_HH_OPEN_EVT`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/src/btif_hh.cc#L772-L815) assigns the Bluetooth address to `p_dev`, requests descriptor information, and emits the existing HAL CONNECTED notification. The descriptor callback currently selects shared `p_curr_dev` then may trigger `UHID_CREATE`, without a request-bound Java grant.

**Design implication:** A patch that only registers an enrolled DS3 at `BTA_HH_OPEN_EVT` risks being late relative to first kernel-facing activity. **The safe default is provisional for every new fd**, and to deny UNKNOWN as well as CANDIDATE until trusted Native + Java standard proof can be linked. The old v2 candidate-only fence allowed any fd not already registered, which cannot enforce registration-before-event.

## Committed offline artifacts

- `experiments/m3-ds3-cable-session/provisional_uhid_gate.h`: C++17 `ProvisionalUhidGate`. `Open(fd,handle)` mints a unique **local fd-open generation**, not a fabricated ACL epoch. An UNKNOWN, PROVISIONAL, CANDIDATE or QUARANTINED fd is denied `UHID_CREATE` and `UHID_INPUT`. `UHID_DESTROY` remains allowed. Every write and close transition uses the same mutex as the final write callback.
- `experiments/m3-ds3-cable-session/test_provisional_uhid_gate.cc`: **20 named host scenarios** including UNKNOWN-before-open, provisional, candidate-no-grant, normal symbolic authenticated/bonded path, every missing standard proof dimension, handle/fd collision, registry saturation/abort, quarantine, failed close, stale close, fd reuse, and input-after-disconnect.
- `experiments/m3-ds3-cable-session/h618_uhid_provisional_v3_disabled.patch`: default-off source-shaped H618 patch in **`system/bt/btif/co/bta_hh_co.cc`** plus a new header `retrobox_provisional_uhid_gate.h`. It puts `Open()` in **both fd open branches, before `hh_keep_polling` and polling thread**, and replaces `uhid_write` with the lock-held callback variant when `RETROBOX_DS3_UHID_PROVISIONAL_V3_RESEARCH` is defined. Failure immediately closes the new fd; new-slot registration failure also restores `device_num`, handle/attr/subclass/app-id/local_vup fields.
- `experiments/m3-ds3-cable-session/verify_h618_uhid_provisional_v3.py`: source shape and header checks; strict G++ host run, then ASan+UBSan run; optional read-only `git apply --check` against the **exact** pinned H618 commit.
- `experiments/m3-ds3-cable-session/run_cpp_host_tests.sh` now invokes the verifier.

### Actual verification

The **exact source bytes committed on GitHub** for header and host test match locally compiled blobs:

```text
provisional_uhid_gate.h       8410b96b988fa52b19ccfc34ed2bbc8919c38794
test_provisional_uhid_gate.cc df7fd878960853cdb339109285acaca938ac4b4b
```

Strict local Linux compiler runs:

```text
g++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread test_provisional_uhid_gate.cc -o test_v3
./test_v3
20/20 PASS (provisional UHID session lifecycle host)

g++ -std=c++17 -Wall -Wextra -Werror -pedantic -pthread -fsanitize=address,undefined -fno-omit-frame-pointer test_provisional_uhid_gate.cc -o test_v3_san
ASAN_OPTIONS=detect_leaks=1 ./test_v3_san
20/20 PASS (provisional UHID session lifecycle host)
```

All **five modified-file hunks** matched the exact pinned H618 source and valid unified diff old/new counts/offsets; the new header was compared byte-for-byte to the host version. **Full BSP `git apply --check`, Android Soong/ABI build and M3 runtime test were NOT performed**; the matching full BSP is absent from the operator's earlier PR #51 readiness environment. The committed Python verifier was NOT independently run in this increment. All 20 are host model scenarios, **not 20 on-device tests**.

## Why the v3 patch must remain DISABLED

1. **There is no trusted Native/Java standard proof producer or call to `PermitStandard` in the source patch.** Thus enabling `RETROBOX_DS3_UHID_PROVISIONAL_V3_RESEARCH` as-is would **block ordinary bonded HID CREATE/INPUT as well**. The host model demonstrates theoretical standard release with symbolic booleans; it does **not** integrate an authenticated BTM/ACL epoch or actual Java `okToConnect` reply. The model is a prerequisite and **not deployable**.
2. `MarkCandidate` is only a state label and has no grant operation. USB report F2/F5 + MAC match remains candidate discovery; it is not proof that the radio peer is the attended DS3. No unbonded security exception, LinkKey spoof, HCI success forgery or `BOND_BONDED` bypass exists.
3. **No actual fd-close lifecycle** is wired into the source patch. The existing `bta_hh_co_destroy(fd)`, failure and reconnect paths call `close(fd)` directly. This leaves stale provisional tokens and risks future registration failure or fd-number reuse. A full integration must carry exact open-generation through BTA/BTIF device lifetime, centralize all close paths, and avoid double-close. The v3 patch intentionally contains no false cleanup hookup.
4. In the reconnect path an existing, still-open fd skips the new `Open` call; that fd must have an existing valid token, or UNKNOWN writes will be refused. Service restart, BTA reentrancy and polling-thread ownership are unverified.
5. The `WithWrite` callback keeps a mutex across the UHID system call. This avoids the modeled check-then-write race but requires a real blocking/lock-order analysis before any Android use.
6. **Root DS3 fault is still HCI authentication timeout `0x22`.** Provisional UHID safety cannot solve the wireless pairing handshake, Sony F4 HID activation, Android bond policy or RetroArch wireless operation.
7. The v1 and v2 fences are **archived research artifacts**. Do not apply any combination of v1/v2/v3 patches; v3 is standalone against pristine pinned H618. The flag is **unset** in Android build configs, and no M3 operation or patch merge is authorized.

## Next practical engineering gate

Before more kernel-side patches, **stop expanding the UHID fence**. The blocking work is:

- a Native device/ACL record with event-bound lifetime that can issue a trusted standard-HID security verdict (not a MAC-based claim), plus asynchronous Java approval; 
- actual safe fd ownership/close across all source branches and normal bonded-device regressions;
- matching full source tree + Android build and explicit owner-approved, independently recoverable one-shot target test; 
- separate source-first investigation of DS3 legacy HCI authentication `0x22` with a bounded and owner-reviewed risk decision.

**Decision:** v3 offline race/ordering model and source context audit PASS; real Native classification integration and wireless support **NO_GO**. PR #52 stays Draft. PR #50 reverse engineering and PR #51 source build are unchanged.
