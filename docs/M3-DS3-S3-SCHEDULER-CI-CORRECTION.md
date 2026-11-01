# S3 CI coverage correction and bounded multi-producer scheduler

**2026-11-01.** Scope: offline model/tests only; no M3 operations, no BSP build.

## Corrected CI evidence

Historical `run_host_tests.sh` compiled the first and second C++ test into the same output path, then ran that **second executable twice**. Hence earlier green CI did **not** demonstrate execution of `test_transaction_owner.cc`. This was detected by reading the script and fixed in commit `327fe6cb`: each test now receives a distinct executable and is run immediately after compilation, with a visible `RUN <name>` marker.

This correction supersedes earlier claims that both standalone host test executables passed under GitHub CI. The previous green check was real, but its coverage was overstated.

## Scheduler experiment

`test_multi_producer_scheduler.cc` models:
- a single active transaction per HID handle;
- bounded pending jobs (maximum three) across kernel UHID, UHID output and HAL producers;
- origin validation (nonkernel jobs may not contain a UHID kernel ID);
- isolation across handles;
- permanent quarantine and queue cancellation on completion, timeout or disconnect.

**No queued job is automatically promoted** after an untagged completion. This is conservative by design: the pinned Fluoride callback does not retain original request/session identity. Queueing by itself cannot establish safe dispatch ordering. The test model is **not a deployable scheduler** and intentionally remains unusable for continuous gamepad input until a proper native control-channel transaction ownership mechanism is proven.

## Follow-on acceptance

Before relaxing quarantine:
1. Trace BTA/HID command serialization and every producer (UHID SET, UHID OUTPUT, HAL, GET/SET protocol).
2. Establish whether completion can be tied to unique command identity across failures, timeouts and disconnect/reconnect.
3. Document command queue fairness, cancellation, resource bounds, and exact mapping of native failure status to UHID error.
4. Verify host tests under actual CI, and then separately compile pinned Android12 Fluoride for ARM32 with Soong; compare ELF/ABI to the private OEM artifact.
5. Resolve DS3-specific native authentication and Android Java HID Host gate independently. No global Bluetooth security weakening.

M3 live execution, injection, library replacement, flashing, service restart and merge remain **NO_GO**.
