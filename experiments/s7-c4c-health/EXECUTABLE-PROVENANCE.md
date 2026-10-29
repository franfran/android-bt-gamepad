# C4C-3 executable provenance (read-only)

Use from the Mac repository checkout with the M3's existing Wi-Fi ADB session:

```bash
python3 experiments/s7-c4c-health/read-only-exe.py YOUR_ADB_SERIAL
```

The script reads the current Bluetooth process ID, status, comm, direct parent status and both processes' `/proc/PID/exe` symlink targets. It validates identity and repeated process status and outputs **only executable categories**: `APP_PROCESS_BINARY`, `PARTITION_NATIVE_BINARY` or `UNKNOWN`. No executable paths, PIDs, arguments, home addresses or raw maps are emitted. Error output is generic.

**Interpretation:** `/proc/PID/exe` describes the running executable image, not an authoritative app launch trace; an Android Zygote child can continue to point to `app_process32`. Direct-parent identity can be affected by reparenting. A native executable category is still not evidence of a particular namespace or the Bluetooth call site's `dlopen` permission.

No service stop/restart, ptrace, injection or device configuration changes. `launch_mechanism`, `caller_linker_namespace` and `addon_path_permitted` deliberately remain `UNVERIFIED`; decision stays `NO_GO`. Wi-Fi first, USB last-resort backup. These tests do not establish recovery from a hung linker.
