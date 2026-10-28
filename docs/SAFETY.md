# Safety boundary, rollback and public repository hygiene

**CURRENT GATE: NO-GO for live Bluetooth injection.** All useful memory/function-call evidence comes from isolated, owned processes; real Bluetooth has 48–49 independent threads and Bionic linker namespace/locks.

**Do not execute the obsolete `bt_inert_inject` binary or its `inject` mode.** It had target-stack scratch (`SP+256`), unbounded waits, invalid return trap and raw PTRACE_PEEKDATA handling. It was intentionally excluded from this repository snapshot. Do not repurpose `experiments/s7-c1/` for arbitrary PIDs: it uses a fork-owned child and a return trap not guaranteed in Bluetooth.

S7-C4B `injection_authorized=false` is deliberate and correct. Neither `SELinux Permissive`, a clean `TracerPid`, nor a calculated `dlopen()` address proves linker namespace acceptance or safe rollback. If a real linker call hangs, CPU register restoration does not undo linker internal changes; entering `QUARANTINE` and stopping further attempts is safer than auto-retry.

Before *any* actual Bluetooth `dlopen`: validate independent device control if Bluetooth fails, plan for controlled service restart, ensure there is no unreviewed boot hook, use dynamic PID and ELF hash, verify stack/trampoline/remote-scratch lifecycles, demonstrate namespace acceptance in a safe process context, and obtain explicit owner approval for one-time experiment with a physical recovery route.

Staging cleanup (`stage.py <ADB_SERIAL> cleanup`) only removes the staged inert add-on; it does **not** unload already mapped code. A non-persistent injected library normally leaves the process when that process exits, but restarting a service is disruptive and does not necessarily repair arbitrary corrupted process state. Never promise unconditional rollback.

Public Git history should not contain raw HCI snoop logs, PIN/LinkKeys, actual device MACs, local home address/IP, signed vendor APKs or `.so` files, or secrets. Audit files have been selected/sanitized; retain originals privately. Some old research scripts are archived for provenance and are **not automatically safe** for future systems.
