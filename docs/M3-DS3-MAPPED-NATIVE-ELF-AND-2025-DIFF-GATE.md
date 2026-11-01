# M3 DS3 — Exact mapped native library and firmware delta verification gate

**2026-10-31 read-only follow-up.** Earlier original S7 owner evidence, not a guessed AOSP install path, establishes the running Bluetooth process actually mapped **`/system/lib/libbluetooth.so`** on the installed 2024 ARM32 M3. The mapping includes RX segment file-offset `0x119000`; observed ASLR bases in that archived snapshot MUST NOT be used as patch addresses.

## Confirmed source
Owner archived `s7-evidence.json`:
- `maps["/libbluetooth.so"]` includes mapped path `/system/lib/libbluetooth.so` across read and executable segments.
- Exact installed owner ELF SHA-256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85` anchors prior S8 reverse engineering.
- S7-C4B evidence for live Bluetooth had `addon.mapped=false`, `injection_authorized=false`, and still lacked linker-namespace acceptance and safe post-dlopen rollback; no live trial has been authorized.

## Next appropriate offline native comparison

The 2025 M3 **International** firmware was previously extracted as an `h618_jjx_english_20250303-1532.img` / dynamic `super` / `system_a.img` by the Owner. Its native Bluetooth ELF has **not been provided or verified in the currently accessible files**, so do NOT fabricate a 2025 native hash, assert binary equality, or tell the user a comparison is complete.

If the Owner has the extracted 2025 `system_a` folder/image locally, choose the exact **`/system/lib/libbluetooth.so`** relative path (note extraction may prefix `system/` in the mount; locate by final filesystem path and verify ELF32 ARM), then compare read-only:

```sh
file /private/original-2024/libbluetooth.so /private/extracted-2025/libbluetooth.so
shasum -a 256 /private/original-2024/libbluetooth.so /private/extracted-2025/libbluetooth.so
readelf -n /private/original-2024/libbluetooth.so | grep -i -A3 'Build ID'
readelf -n /private/extracted-2025/libbluetooth.so | grep -i -A3 'Build ID'
```

If hashes differ, **do not automatically assume DS3 behavior changed**: target S8 `hidh_conn_reg` security registration and incoming pre-auth caller equivalence must be analyzed with original 2025 symbol/layout first. Do NOT use old firmware VMAs as new firmware offsets. Check ELF signature/architecture, native dependencies and service behavior separately.

## Why this matters

- A hypothetical static library patch on M3 targets the already-measured **`/system/lib/libbluetooth.so`**, not a modern Android Bluetooth APEX path. Modifying that ELF on disk may affect AVB/verity and the entire Bluetooth process; this is **no authorisation to patch it**.
- Runtime addon may avoid changing this system ELF, but must safely enter live BT process **and** attach a real policy callback, while handling the independent Java `BOND_BONDED` gate.
- The 2025 Java APKs were byte identical and relevant PIN-framework methods unchanged; this *does not* prove 2025 native ELF is identical.
- A/B support without verified inactive slot / USB ADB recovery is NOT a safe rollback plan.

## Decision
**NO_GO for live patch/injection**, S7 Issue #6 unchanged. **GO** only for offline native fingerprint comparison on privately retained original files, if available. Already completed USB sixpair enrollment and RetroArch wired input PASS are not to be repeated.
