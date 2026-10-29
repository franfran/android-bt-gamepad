# S8: bounded offline HID BLX dispatch investigation

The saved M3 ARM32 mini-debug callgraph confirms several `hidh_l2cif_connect_ind` branch targets are **unresolved**, including `0x5dee60`, `0x5deea0` and `0x5df050`. A `blx` to a numeric target is a *direct* call to that address; it is **not by itself proof of an indirect callback**, and the target might be a veneer/PLT stub. Treating it as a confirmed security callback would be incorrect.

The next material work is **to disassemble those precise targets from the historical original M3 `libbluetooth.so`**, if a private local copy remains. This tool bounds the review to 32 bytes per candidate and does not attach to any process, modify Bluetooth, or patch code.

```sh
python3 experiments/s8-veneer/inspect_dispatch.py research/retrobox-stage3c-callgraph.txt
# If and only if you already have the original M3 library privately on your Mac:
python3 experiments/s8-veneer/inspect_dispatch.py research/retrobox-stage3c-callgraph.txt --elf /private/local/libbluetooth.so
```

The first command is fully reproducible against repository material and lists exact unresolved addresses/callsites. The second is optional, offline, and prints bounded disassembly from local original bytes. **Never commit/upload the proprietary library or raw dumps.** Existing upstream historical M3 binary fingerprint should be checked before using its offsets; another build may have different ELF VMAs. The tool does not certify the binary provenance itself.

The output deliberately maintains `callback_resolution=UNVERIFIED` and `security_path_proven=false`, even when disassembly is present. A reviewer must inspect branch instruction semantics, potential PLT relocations, and actual callback table writes; evidence is not obtained merely by reaching a veneer.

Prior confirmed context remains unchanged: DS3 HID Control PSM `0x11` preceded HCI Authentication Requested; authentication ended `0x22`. The HID registration mask `0x36` applies to all HID devices; do not patch it globally. The Android 12 `btm_sec_l2cap_access_req_by_requirement` interface lacks an explicit PSM parameter; preserve per-device and per-service context if designing a scoped fix.

**Gate:** No live injection, service restart, root radio operations or security policy changes; C4C-3 remains NO_GO. CI tests only classify archived callsite evidence, not Bluetooth interoperability.
