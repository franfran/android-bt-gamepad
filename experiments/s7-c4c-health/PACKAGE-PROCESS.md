# C4C-3 package/process correlation, read-only

Run on the Mac using the existing M3 Wi-Fi ADB connection:

```bash
python3 experiments/s7-c4c-health/read-only-package-process.py YOUR_ADB_SERIAL
```

Checks the live Bluetooth process identity/UID and the installed `com.android.bluetooth` package UID through `pm list packages -U`. Reads the process's first `cmdline` field only to determine whether it **exactly equals** `com.android.bluetooth`; raw command lines and PIDs are never displayed. Performs a second PID/status comparison. Requires the same normal-state Bluetooth UID 1002 observed in prior M3 checks; unexpected state fails closed.

If package UID and process UID match **and** the process name exactly matches, the tool reports `package_process_association=CORROBORATED`, meaning matching metadata evidence, *not* a cryptographically proven package binding. Android's shared UID allows multiple APK packages to have the same Linux UID. Process name can also be configured and cannot establish exact loaded APK or classloader. A mismatching package UID reports UNVERIFIED rather than accepting the association.

The tool may return generic `read-only package/process lookup unavailable` on OEM `pm` output differences. In that case do not alter device configuration to make it pass; evaluate parser compatibility separately. The tool does not perform a load, restart, injection, ptrace or recovery operation.

Even a corroborated association leaves `apk_classloader_link`, `caller_linker_namespace` and `addon_path_permitted` UNVERIFIED; live Bluetooth remains NO-GO. Existing Wi-Fi ADB remains primary, USB is owner-confirmed normal-state last resort.
