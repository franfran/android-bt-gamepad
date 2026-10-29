# C4C-3 launch-provenance read-only observation

Host-side tool (no Android NDK), based on the reviewed C4C-3 namespace-selection plan.

```bash
python3 experiments/s7-c4c-health/read-only-launch.py YOUR_WIFI_ADB_SERIAL
```

Reads only the *current* Bluetooth PID, process comm and status, and its directly referenced parent's comm/status; validates child PID and parent relationship during one snapshot. Outputs only coarse parent classification: `ZYGOTE_PARENT_OBSERVED`, `NON_ZYGOTE_PARENT_OBSERVED`, or `UNKNOWN`, never raw PID, parent name, command line, arguments, mappings, home IP, MAC or memory address. No filesystem writes, ptrace, process stop, Bluetooth restart or library load.

**Important interpretation:** This is an observed **direct parent**, not conclusive proof of application launch mechanism. In Android a Zygote-derived process can have a different parent after reparenting, and an OEM might use other launch patterns. Even a Zygote parent result cannot tell which linker or classloader namespace handles an actual `dlopen` call. Do not promote `launch_namespace`, `caller_linker_namespace` or `addon_path_permitted` from `UNVERIFIED`.

Owner preference remains Wi-Fi ADB first, USB ADB last-resort fallback. This tool never performs recovery; live Bluetooth service injection remains NO-GO.
