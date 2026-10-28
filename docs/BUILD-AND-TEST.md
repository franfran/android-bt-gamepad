# Building and testing from this snapshot

## No NDK on the operator Mac

The experiment folders contain C/Java/Python source and selected ARM32 prebuilt binaries compiled in a sandbox. Many were originally compiled with Clang 17 + LLD using freestanding ARM32 Linux syscalls or with Android dynamic linker import assumptions. These are **research binaries**, not reliable release builds across Android devices. Individual folder READMEs describe their original dependencies and constraints.

For current *read-only* integration after staging (no Bluetooth injection):

```bash
cd experiments/s7-c4b
python3 -m unittest discover -v
python3 s7c4b.py <ADB_SERIAL> --output s7c4b-evidence.json
```

For resolver local unit tests:

```bash
cd experiments/s7-c3-resolver
python3 -m unittest discover -v
```

For staging verify/cleanup (modifies only the test staging dir, **not** the system Bluetooth libraries):

```bash
cd experiments/s7-c4a
python3 stage.py <ADB_SERIAL> check --output check.json
# Only if necessary and explicitly intended:
# python3 stage.py <ADB_SERIAL> cleanup --output cleanup.json
```

The first test run on a fresh box requires staging from `experiments/s7-c4a/`; do not mistake staging for injection.

Some archived `run-on-m3.sh` scripts are experimental and may attach an owned test process or a Bluetooth leader. **Do not run them automatically or as an overall test suite.** Especially never run the old superseded Bluetooth injector.

## Provenance, binary/vendor data and limitations

User logs indicated success/failure for each milestone; see `docs/STATUS.md`. Code comments and stage README files may contain pre-test "expected output" that was subsequently superseded by actual device results. The repo deliberately excludes manufacturer-extracted Bluetooth APK/.so, raw HCI logs and any private PIN/LinkKey information; if binary forensics need repeating, collect source privately and record SHA-256 only.

Certain source files contain device-specific assumptions from the original prototype (like fixed test MACs): these have been replaced with **non-operational example values** for a public repository; explicitly configure a verified controller/host address for any future diagnosis, without committing real identifiers.
