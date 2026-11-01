# S3 host-only transaction ownership prototype

Source files:
- `experiments/m3-source-first/transaction_owner.h`
- `experiments/m3-source-first/test_transaction_owner.cc`

Run from repository root:

```sh
c++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  experiments/m3-source-first/test_transaction_owner.cc \
  -o /tmp/m3-transaction-owner-test
/tmp/m3-transaction-owner-test
```

2026-11-01: equivalent source compiled and executed on sandbox Linux host with GCC 14.2.0; printed `transaction ownership host assertions PASS`. The committed test and header have been transcribed into this PR. This is **host-only**, not ARM32 Soong validation. No M3 interaction.

**Model semantics:** cross-producer one-in-flight per HID handle; reject simultaneous kernel SET, UHID OUTPUT, HAL SET, GET and SET_PROTOCOL; preserve original UHID ID and raw status; model synchronous send failure; reject timeout/late callback, duplicates, invalid timeouts, overflow and same-handle reconnect. Other handles remain isolated. Only a KernelUhidSet origin may carry a kernel request ID.

**Critical limitation:** `finish()` returns an **observation**, never a UHID kernel reply. Because pinned Fluoride's `bta_hh_co_set_rpt_rsp` callback has no transaction token, an apparently valid completion may still be a stale handshake. This model **permanently quarantines even successfully completed handles**, preventing a subsequent request from receiving a stale callback. That fail-closed choice is intentionally too strict for a useful runtime controller. Native source integration requires identity-preserving BTA-level serialization and tested session retirement or a proven alternate completion contract before relaxing it. Never merge this toy model into an Android production library as a functional DS3 fix.

**Remaining:** source patch unimplemented; auth/HCI 0x22, OEM Java bond check and kernel UHID reply remain separate gates; offline ARM32 `libbluetooth.so` not built; live operations NO_GO.
