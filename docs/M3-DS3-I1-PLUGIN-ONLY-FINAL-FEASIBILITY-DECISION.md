# PR #52 — M3 onboard-radio DS3 **removable plugin**: bounded engineering decision

**Date:** 2026-11-02. **Scope:** iMETBOX M3 original installed Android 12 Bluetooth controller + OEM `libbluetooth.so` retained + normal Bluetooth retained + genuine DS3 -> Android input -> RetroArch. **Owner requested a plugin-feasibility determination, not an alternative architecture build.** This is a research **stop/go decision**, not permission to merge/close this PR, change system files, restart M3 Bluetooth, or start a USB dongle PR.

## Executive decision: STOP investing in an ordinary standalone plugin

**Decision:** **NO_GO as an engineering implementation for any presently identified, supported removable APK/native `.so` plugin interface.** We have **no verified entry point** that gives an externally installed component sufficient authority over **all** of DS3's native Classic authentication + HID PSM policy, Java HID Host admission, and UHID report transactions *while OEM Bluetooth continues unchanged*.

**Residual bounded uncertainty:** An **undocumented, exact-OEM private loader/registration/IPC ABI** is **UNRESOLVED**, not disproven, because original M3 proprietary ELF/JNI/APK raw bytes could not be accessed in this session. Therefore **DO NOT** advertise a proof that a Bluetooth plugin is logically impossible or that every stripped OEM function has been examined. It is nonetheless **NO_GO to begin writing an implementation** without a real loader and full callback/lifecycle contract. Another general AOSP/H618 research cycle will not close that exact-OEM evidence gap.

**Decision question:** Should PR #52 remain an *evidence-locked Draft* awaiting exact original bytes, or be closed as **NO_GO for supported interfaces examined**? Either disposition is safe; **do not merge misleading speculative adapter code**. The scope and residual gap belong in PR #52 whatever Owner chooses.

## What was genuinely inspected and falsified

| Candidate that initially looked promising | **Measured / source-proven** evidence | Bounded decision |
| --- | --- | --- |
| Ordinary external Bluetooth **APK** plugin | [Pinned Android 12 and M3 pairing audit](M3-DS3-I1-ANDROID-PAIRING-BINDER-JNI-PLUGIN-REACHABILITY.md): `ACTION_PAIRING_REQUEST` and `BluetoothDevice.setPin(byte[])` provide **only a potential PIN handoff** subject to `BLUETOOTH_CONNECT`/bond state; Android manifest-only implicit receiver limitations still apply. **Real M3** TV Settings owns `.bluetooth.BluetoothPairingRequest` as **PRIVILEGED** app with `BLUETOOTH_PRIVILEGED` granted. | **NO_GO as full DS3 plugin**: a first-stage PIN handler is not authority to change native HID auth, Java bond, or UHID |
| Exported **HidHostService Binder** | H618 `HidHostService.connect/disconnect` enforce `BLUETOOTH_PRIVILEGED`; `AdapterService` and `Config` start a predefined list of internal profiles. | **NO_GO as externally registered HID policy plugin**. Even calling privileged connect would not supply an auth/security callback |
| New **OEM service** installed in Bluetooth app | Actual M3 package-manager `Service Resolver Table`: all **22 distinct intent-resolvable Bluetooth service classes** match the [pinned public manifest](M3-DS3-I1-OEM-SERVICE-RESOLVER-AND-HIDL-EXTENSION-BOUNDARY.md): **22/22, zero unexpected names**. [CI 41483377579](https://github.com/franfran/android-bt-gamepad/actions/runs/41483377579) SUCCESS (11 synthetic tests; 10 SHA-pinned public blobs; 22 mapped names). | **Bounded negative** only for *extra named intent-resolvable services in this original M3 snapshot*; hidden Binder/no-filter service/modified method **not** excluded |
| OEM `libbluetooth.so` **dynamic loader** | Original M3 process maps `/system/lib/libbluetooth.so`; `libdl.so` mapped. Public `AdapterService` JNI fixed `dlopen("libbluetooth.so")` loads **entire stack**, not companion. `dlsym(RTLD_DEFAULT)` resolves existing internal `module_t` and static `BT_PROFILE_HIDHOST_ID` selects `btif_hh_get_interface()`. | **NO external plugin loader proven**. A mapped linker or isolated `dlopen` does not make an OEM extension API |
| Native HID Host **callbacks** | H618 JNI first cleans old HID interface then binds native `init(&sBluetoothHidCallbacks)`; BTIF has one `bt_hh_callbacks` pointer, not a per-plugin subscriber list. | **NO_GO** for safe second callback owner without OEM multiplexer |
| Independent same-controller Classic **L2CAP PSM** listener | Existing HID Host owns fixed **PSM 0x11/0x13** with authentication+encryption; pinned L2CAP RCB can overwrite `p_rcb->api` on competing registration. | **NO_GO** for trial same-controller fixed PSM registration: can clobber OEM handler; not a plugin |
| Dedicated vendor **Bluetooth HIDL HAL** | Actual M3 `init.svc.vendor.bluetooth-1-0=running` in archived property snapshot; standard HAL `initialize(IBluetoothHciCallbacks)` and HCI/ACL transport callbacks are an owned **controller transport**, not HID security/Java/UHID admission. | **NO supported profile plugin / safe multi-client HCI broker found**. Do not initialize a second HAL client |
| **Interop/config** exception | Public `interop_database_add` supports existing predefined enums, not arbitrary per-peer HID policy, Java bond or UHID code. Android fixed profile class table is not a plugin catalog. | **NO_GO as complete DS3 compatibility plugin** |

### Three actual original M3 protocol/input gates remain separate

1. **Native Classic HCI and HID L2CAP security**: Original M3 S8 native research found HID PSM 0x11/0x13 security registration. Four **2026-10-29/30** contiguous HCI attempts show HCI `PIN Code Request` with **no observed host HCI PIN reply** before HCI **Authentication Complete event status `0x22` = LMP Response Timeout** ~30.06s later (see [four-session audit](M3-DS3-I2-UPLOADED-HCI-FOUR-ATTEMPTS.md)). A **different, earlier** archived Stage 3A observation described a 6-byte HCI PIN reply which also did **not** establish successful auth. **These are different historical attempts; do not conflate them, or assert the PIN reply is always missing.** No captured reply or wrong PIN alone explains all sessions, and 0x22 is **not** error `0x05 = Authentication Failure`.
2. **Native->Java HID admission**: Original SHA-matched M3 Bluetooth APK/DEX research [PR #50 evidence](https://github.com/franfran/android-bt-gamepad/blob/plan/m3-ds3-privileged-pin-helper/docs/M3-DS3-HID-DEX-AND-NATIVE-GATES.md) directly found `HidHostService.okToConnect()` rejects `BOND_BONDED`-false peers on a mapped `Message.what=3` handler branch. Live DS3 execution of that exact Java handler is *not* independently confirmed when native security fails earlier.
3. **UHID/RetroArch**: Original native/UHID source-correlated reports show missing `UHID_SET_REPORT_REPLY` handling in the known path. Wired DS3 works in RetroArch, **wireless input is unproven**, and a Bluetooth pairing notification is not enough. No external plugin authority to supply transactional UHID callbacks was found.

A BlueZ Sixaxis plugin implements **a different in-daemon plugin loader plus USB cable enrollment / HID security behavior**. It cannot be copied as an Android installable plugin, and global security relaxation/forged bonds are out of scope.

## Exact-OEM binary closing test — one limited unresolved item, NOT another research loop

**Owner original exact-OEM identities, private:** `m3-original-2024-libbluetooth.so` original SHA256 `4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85`; ELF Build ID `0d29a62178e43066e018216c1f1d5b18`. Original M3 JNI SHA256 `1db644b6e2203431e95d55d420729db054fa7f2f8e0bd2f8cbd35a00abf17dfd`; original Bluetooth APK SHA256 `d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f`. A previously inspected 2025 Android APK comparison is **not** a 2024 native loader proof. Do not upload these proprietary files or addresses to public GitHub/CI.

### Recovery of the original M3 **mini-debug symbol-table investigation** (ready but NOT run on OEM bytes)

Earlier [Stage 3C Gate 2 exact-OEM source-provenance report](../research/retrobox-stage3c-gate2-native-symbol-recovery.md) recorded that the **original owner-verified** 2024 `libbluetooth.so` contains an XZ-compressed `.gnu_debugdata` mini-ELF with a native symbol table. This is a materially stronger **available inspection technique** than searching ELF `strings` alone. That historical report directly recovered `hidh_conn_reg()`, `hidh_l2cif_connect_ind()`, `btm_sec_mx_access_request()`, `btm_sec_auth_complete()`, etc. It did **not** establish any OEM removable plugin loader.

To preserve this capability in PR #52, committed [original M3 mini-debug plugin-symbol triage](../experiments/m3-ds3-compat-adapter/audit_oem_minidebug_symbols_offline.py). It validates **original exact SHA + Build ID** before parsing embedded XZ mini-ELF; extracts with strict section bounds and 16 MiB decompression cap; uses a private ephemeral file for readelf; prints only *predeclared known symbol names* and a **count** of other plugin-looking names, never raw private symbols, addresses, paths, PINs or link keys. A nonzero count is **triage only** and absolutely **NOT a plugin ABI/callsite**; a zero count is **not proof of absence**.

The [17 existing ELF metadata tests + 9 new mini-debug gate tests](https://github.com/franfran/android-bt-gamepad/actions/runs/41485321125) completed **SUCCESS**: decoded GitHub Actions log confirms **17 tests / OK**, then **9 tests / OK** at workflow commit `11b399f6`. **All 26 tests use only synthetic host objects**. No proprietary M3 ELF was supplied to CI or inspected by either checker, because access is denied in this research session.

If private 2024 original binary is later available on a trusted host, run read-only:

```bash
python3 experiments/m3-ds3-compat-adapter/audit_oem_plugin_elf_offline.py \
  /PRIVATE/ORIGINAL/libbluetooth.so
python3 experiments/m3-ds3-compat-adapter/audit_oem_minidebug_symbols_offline.py \
  /PRIVATE/ORIGINAL/libbluetooth.so
```

These probes **cannot themselves deliver plugin GO or comprehensive OEM NO_GO**: follow any plausible actual loader/registration symbol through disassembly/ABI/callsite and subsequent BTM/HID/Java/UHID authority. Do not upload inputs or raw results that might identify private devices.

**This session explicitly attempted authorized raw-byte access** to original 2024 ELF, JNI zip and APK zip from the Owner's previously uploaded Library records. The file system returned `This Project file does not have an authorized raw-byte materialization path` for each. Container `/mnt/data` held no uploaded original bytes. The previously committed [fail-closed original ELF metadata auditor](../experiments/m3-ds3-compat-adapter/audit_oem_plugin_elf_offline.py) **could not be run against real OEM bytes**; host synthetic tests only validate auditor behavior. It is dishonest to mark this missing test PASS or imply no `dlopen` import in original.

**If private original bytes become available in a later authorized session**, the ONLY remaining plugin-oriented examination is:

1. On a trusted **offline host**, SHA/build-ID-verify original ELF, JNI, APK and exact vendor HAL/extension binary where known. Run `python3 experiments/m3-ds3-compat-adapter/audit_oem_plugin_elf_offline.py /PRIVATE/ORIGINAL/libbluetooth.so` (requires `readelf`, `strings`; outputs only sanitized allowlisted metadata). Do **not** put any private binary in Actions.
2. Audit **actual** OEM `dlopen` / `android_dlopen_ext` / `dlsym` / module enumeration callsites (not merely strings/imports), relevant manifest/DEX dynamic class loading, HIDL/Binder vendor registration, and Android linker namespace acceptance. For every **positive** candidate, demand exact loader identity, documented or reproducibly inferred input ABI, caller, timing, permissions, and unloading contract. Missing imports in stripped ELF do not by themselves prove absence.
3. Only **if** a true supported load/IPC endpoint exists, show on paper how it can legitimately supply **per-device** native HCI/BTM/HID security + Java `BOND_BONDED` admission + UHID SET_REPORT transactions **without** changing original core libraries or breaking unrelated Bluetooth. **No plugin GO until all mandatory gates and safe cleanup satisfied.**
4. If inspected original binaries show no qualifying path, record **`NO_GO for 2024 M3 OEM examined ABI`**, with file hashes, coverage and blind spots. If original bytes remain inaccessible, outcome is **`supported plugin implementation NO_GO; proprietary OEM-only absence not proven`**. **Do not prolong general public-source research** trying to substitute for exact OEM bytes.

**No device action is required for the current conclusion**. Original ELF inspection is a separate optional offline evidence completion when privately accessible; do not ask Owner to reinstall apps, repeat USB sixpair, restart Bluetooth or re-run invasive probes.

## Owner-facing engineering recommendation

**Stop PR #52 implementation activity now.** There is no demonstrated removable plugin target to write against. Maintain Draft / issue record, with **NO_GO for standard public/installed M3 supported interfaces** and **UNRESOLVED original private loader until actual raw bytes examined**. If the Owner later authorizes a different architecture, open a **separate PR** with explicit scope; **neither PR #51 source rebuild nor USB dongle is authorized by this research decision**. Distinguish *plugin architecture failure* from *DS3 wireless impossible*: prior HCI and original OEM native/DEX findings show concrete compatibility gates, not a proof the radio can never support DS3.

**Security/scope:** No original proprietary binary public upload, M3 operation, new installation, root injection, privileged Binder trial, system modification, Bluetooth restart, PIN/link-key fabrication, disabling encryption, opening HID fixed PSMs, USB dongle research, BSP build or PR merge.
