# RetroBox Stage 3D S1 safety harness — ARM32 v2

**Fix:** ARM32 `mmap2` syscall return addresses may be >= `0x80000000` and thus negative when interpreted as signed. The old test `((long)S < 0)` incorrectly rejected valid mappings. Version 2 uses Linux's actual errno range (unsigned return >= `0xfffff001`) and prints numeric errno if mapping really fails.

**Scope:** No Bluetooth access, no external PID, no injection, no remote calls, no persistent changes. The executable traces only its own created child process, uses four worker threads, bounded waits and best-effort cleanup.

**Run from Mac (no NDK needed):**

```bash
chmod +x run-on-m3.sh cleanup-m3.sh
./run-on-m3.sh 192.0.2.10:1080
```

This uploads the executable every run into `/data/local/tmp/retrobox_stage3d_safety_s1` and does not rely on files surviving a reboot.

Expected: `SHARED MMAP OK`, `OWNED CHILD PID=...`, `WORKERS READY=4`, then `PTRACE_SEIZE`, `PTRACE_INTERRUPT`, `PTRACE_DETACH`, worker progress and cleanup. Binary compile and ELF checks passed, but not M3 device test. If failed, share complete output.

Cleanup: `./cleanup-m3.sh 192.0.2.10:1080` removes the S1 directory only.

This validates leader-thread pause/resume while worker threads remain active, **not** all-thread suspension or remote dlopen safety. Do not run any old Bluetooth `inject` mode.
