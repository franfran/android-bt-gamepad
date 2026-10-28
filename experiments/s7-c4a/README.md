# RetroBox S7-C4A — Inert Bluetooth Add-on Staging (not injection)

This milestone **actually stages the existing ARM32 inert add-on** under a clean directory and verifies its bytes against the packaged file, rechecks the currently running Bluetooth PID/UID/tracer and whether the add-on is mapped. It does **not** attempt `ptrace`, `dlopen`, `mmap` in Bluetooth, or system modifications. It is not S7-C4 injection success.

## Run from Mac (Python 3 + existing adb, no NDK)

```sh
python3 stage.py 192.0.2.10:1080 stage --output s7c4a-evidence.json
```

To repeat the checks without uploading files:

```sh
python3 stage.py 192.0.2.10:1080 check --output s7c4a-check.json
```

To remove **only** this staging directory:

```sh
python3 stage.py 192.0.2.10:1080 cleanup --output s7c4a-cleanup.json
```

v2 staging avoids `chmod` entirely. It pushes to a shell-writable temporary path under `/data/local/tmp`, then uses `su 0` to copy into the dedicated staging directory; the temporary upload is deleted in a `finally` block. This works even if an earlier failed attempt left a root-owned staging directory. The device may reboot between invocations: `stage` uploads from the Mac package each time. Existing earlier stage folders are untouched. `check` doesn't assume a static PID. Uses root only to read `/proc/<PID>/maps` and the staged file.

## Engineering status and blocking design issue

The validated S7-C1 remote call was performed in a **fork-owned child**. Its return trap lives at a known function address in that same image; this cannot be transplanted into Bluetooth. On a long-running third-party process, remote `dlopen` can interact with dynamic linker locks and async states. A timeout is **not** a reversible transaction. Neither `PTRACE_DETACH` nor register restore can undo an in-progress constructor or linker state. Reboot/restart may disrupt Bluetooth, and no independent watchdog can promise harmless recovery.

Safe next options: (a) inspect/use an established Android ARM32 runtime instrumentation framework with a documented process-attach/cleanup model and explicit operator acceptance of service disruption, or (b) a process-start integration method with rollback. Both require more than this staging test; do not run the obsolete D2b-2d-B `inject` executable.

`S7-C3 v3` address resolver source is included only as a read-only reference. Its computed Thumb pointer is process/ASLR specific and not proof of remote-call safety.
