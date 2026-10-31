# M3 / DualShock 3 Wireless Pairing — Root-Cause Investigation and OEM / Firmware Identity

**Status:** High-confidence conditional software defect; final live variant and exact recovery not yet proven.  
**Recorded:** 2026-10-31. **Device:** iMETBOX M3, rooted Android 12, Allwinner H618.  
**Scope:** Documentation only. Does not authorize firmware flashing, system-APK replacement, privileged APK installation, Bluetooth service restart, native injection, or security relaxation.

## 1. Executive diagnosis

When a Sony DualShock 3 (DS3) initiates legacy Bluetooth pairing, the M3's Java Bluetooth service receives and forwards the PIN request. A separate **vendor TV Settings receiver**, `com.android.tv.settings.bluetooth.BluetoothPairingRequest`, logs `onPair: null` shortly afterward. Reverse-engineering the **actual owner-supplied M3 TvSettings.apk** shows its receiver reads `android.bluetooth.device.extra.PAIRING_VARIANT` and invokes `onPair(variant, null)`. Its **PIN variant 0** branch passes that String value to `BluetoothDevice.setPin(String)`. Reverse-engineering the **actual owner-supplied M3 framework.jar** shows `setPin(null)` returns `false` without sending a PIN to Bluetooth service.

**Conditional root cause:** if the DS3 runtime pairing request has Android `PAIRING_VARIANT_PIN == 0` and follows the observed receiver path, the vendor app submits a null PIN, which the framework rejects; consequently the controller waits and times out. This explains—but does not independently prove every detail of—the user-observed lack of an HCI PIN reply.

**Bug classification:** strongest suspect is **vendor/OEM Android TV Settings (Java application-level pairing handler)**, not the Bluetooth chipset/driver, nor the framework's correct rejection of a null PIN. The original code owner (Oranth vs brand integrator) is **not established**.

## 2. Evidence and confidence

| Observation | Evidence / provenance | Assessment |
|---|---|---|
| DS3 name and legacy PIN request reaches Android Java Bluetooth service | Owner `ds3-pairing-raw.log`; `BluetoothBondStateMachine.pinRequestCallback` at 11:54:23.556 and 11:54:55.938, name `PLAYSTATION(R)3 Controller`, CoD 508 | **Observed** |
| TV Settings pairing receiver runs soon afterward | Same log: `BluetoothPairingRequest: onPair: null` at 11:54:23.904 and 11:54:56.039; PID 846 was `com.android.tv.settings` | **Observed** |
| Receiver unconditionally supplies null at its shown call site | Owner `/system/system_ext/priv-app/TvSettings/TvSettings.apk`, `classes9.dex`, virtual `onReceive(Context,Intent)` code offset `0xeb74c`: reads `EXTRA_PAIRING_VARIANT` then invokes `onPair(variant, null)` | **Static bytecode evidence**, subject to normal control flow |
| PIN branch calls device `setPin(String)` with provided argument | Same DEX, direct `onPair(int,String)` code offset `0xeb65c`; packed-switch first key 0; key 0 reaches `BluetoothDevice.setPin(Ljava/lang/String;)Z` | **Static bytecode evidence** |
| M3 framework rejects null PIN before reaching Bluetooth service | Owner `M3-framework.jar` `BluetoothDevice.setPin(String)` and `convertPinToBytes(String)`: null conversion → null byte array → returns false before `setPin(byte[])` | **Static bytecode evidence** |
| Older HCI session: 4 DS3 PIN requests, no positive/negative PIN replies | Owner btsnoop HCI capture, separate session; following authentication ends with LMP response timeout | **Observed in older session**; cannot claim HCI evidence for Oct 31 logcat pairings |
| DS3's event actually had Java pairing variant integer 0 | Not printed in the supplied logcat | **Not yet observed** |
| Return value of `setPin(null)` on the exact live event | Not logged | **Not yet observed** |
| 2025 M3 firmware resolves this bug | No vendor APK comparison or release note confirmation | **Unknown** |

**Critical accuracy note:** one intermediate investigation update incorrectly labeled code offset `0xeb74c` as `onCreate(Bundle)`; it is actually `onReceive(Context,Intent)`. The error came from not resetting DEX `method_idx_diff` between direct and virtual method groups. Independent DEX decoding corrected this. Do not perpetuate the `onCreate` assertion.

**Security/privacy:** no DS3 Bluetooth MAC, pairing secret, or complete unredacted device logs are published in this document.

## 3. Failure chain / how it maps to layers

1. **DS3 / controller:** initiates legacy pairing and waits for a PIN response.
2. **BT controller / driver + native stack:** passes the PIN event up to Java; observed successful delivery means the request is not lost entirely at HCI/native layer.
3. **Android Bluetooth service:** logs `pinRequestCallback` and emits the Android pairing request.
4. **M3 OEM TV Settings receiver:** observed `onPair: null`, with bytecode `onPair(variant, null)`. **Suspected defect** for variant 0.
5. **M3 Android framework:** rejects null argument by returning false; this is defensive and expected, not the bug.
6. **Result:** when variant=0 and no other handler supplies a valid PIN, no positive HCI PIN reply is sent; authentication can time out.

This is **not** a claim that DS3 wireless pairing can be solved by arbitrary `0000`, generic auto-PIN, or insecure global BTM policy changes. DS3 legacy pairing requires proper host/controller association; preserve existing USB enrollment knowledge.

## 4. Device / firmware identity (captured using read-only adb)

| Field | Value |
|---|---|
| Product/brand reported by user | iMETBOX M3; BigDroidOS 2.0.1 was reported in previous hardware inventory |
| `ro.product.manufacturer` | `Oranth` |
| `ro.product.model` | `M3` |
| Chipset / hardware property | Allwinner H618 family; `ro.hardware=sun50iw9p1`; `ro.board.platform=apollo` |
| Device tree model | `sun50iw9` prefix (output ended with terminal-rendered `%`; no full model inference) |
| Android version | 12 (API 31) |
| `ro.build.fingerprint` | `google/raven/raven:12/SP1A.211105.004/20240412.161509:userdebug/release-keys` |
| `ro.vendor.build.fingerprint` | `google/raven/raven:12/SP1A.211105.004/chenzanchao04121614:userdebug/release-keys` |
| `ro.build.version.incremental` | `20240412.161509` |
| `ro.product.firmware` | `2024041216` |
| `ro.product.device` | `raven` — reported product identity, not actual chipset |
| `ro.product.name` | `raven` — not evidence of Google Pixel compatibility |
| `ro.product.board` | `exdroid` — consistent with Allwinner Android platform naming |
| `com.oranth.upgradeapplication` version | `versionCode=1`, `versionName=22.08.26`, `minSdk=21`, `targetSdk=29`; application version, **not** OTA firmware release date |
| `TvSettings` package/version | `com.android.tv.settings` — versionCode=1; versionName=1.0; targetSdk=31 |
| TV Settings APK | `/system/system_ext/priv-app/TvSettings/TvSettings.apk` |
| Bluetooth APK | `/system/app/Bluetooth/Bluetooth.apk` |
| Android framework JAR | `/system/framework/framework.jar` |
| Bluetooth system package | `com.android.bluetooth` |
| Device firmware upgrade packages | `com.droidlogic.updater`, `com.oranth.upgradeapplication`; also `com.google.android.configupdater` |
| A/B updates | `ro.build.ab_update=true`; partition list contains system/vendor/product/boot and vbmeta partitions |

**Caution:** `google/raven/raven` is the build fingerprint string reported by this TV box; it does **not** establish Pixel hardware or firmware compatibility.

## 5. OEM identity — confirmed versus inferred

### Observed on this particular M3
- Android build property explicitly says **`Oranth`** is manufacturer.
- OTA service domains and upgrade app are branded **oranth**.
- The branded device is **iMETBOX M3**.
- This combination suggests Oranth OEM/firmware involvement, but **does not prove the exact contracting manufacturer, source-code ownership, or which party customized TvSettings**.

### Public OEM / ODM company information
- **Shenzhen Oranth Technology Development Co., Ltd.** publicly describes itself as an Android OTT/IPTV box manufacturer offering **OEM/ODM hardware, firmware and software customization**, including Allwinner platforms.
- Oranth states that it is the original manufacturer and brand owner of **Tanix**; **this does not establish that iMETBOX M3 is a Tanix model**, or that Tanix firmware is interchangeable.
- Official Oranth manufacturer links: https://www.tanixtvbox.com/about-us/ and https://www.tanixtvbox.com/our-history/ .

### iMETBOX firmware evidence
- iMETBOX's website lists an **M3 International (H618)** firmware dated **2025-03-03** and an **M3 Taiwan (H618)** firmware dated **2025-03-04**, later than this device's 2024-04-12 build. https://www.imetbox.net/download.html
- The public listed notes mention voice/language recognition and 5GHz Wi-Fi signal for a newer Wi-Fi module—not a confirmed Bluetooth Legacy PIN pairing fix.
- **Unknown:** whether those packages match this exact M3 board / region / hardware revision; whether any package changes `BluetoothPairingRequest`; whether OEM OTA has an even newer build. Do **not** equate same chipset and product-family name with safe flash compatibility.

## 6. OTA discovery (read-only Android property evidence)

| Property | Value / interpretation |
|---|---|
| `ro.product.otaupdateurl` | `http://www.oranthservice.com:8008/ota/H618_jjx` — likely system OTA endpoint, exact protocol not inspected |
| `dev.xml.url` | `http://www.oranthservice.com:90/apprepo/jjx_618_english/apkupdate.xml` — likely application update manifest, distinct from full firmware |
| `init.svc.update_engine` | `running` at inspection time |
| `ro.build.ab_update` | `true` |

Both endpoint URLs use **HTTP**, not HTTPS. For firmware verification, insist on independently confirmed OEM-origin source, exact device/SKU/hardware revision match, appropriate signed packages, and backup/rollback plan. Avoid triggering OTA install merely to inspect changes.

## 7. Next evidence gates before any fix or update

1. **Runtime variant:** obtain an explicitly logged `PAIRING_VARIANT` value for the DS3 broadcast, or rigorously trace the M3 Bluetooth service code assigning the variant. This is the last major missing link for exact `setPin(null)` execution.
2. **Firmware diff (offline first):** verify precise SKU/region/revision; if an OEM-signed M3 firmware is obtained, extract new `TvSettings.apk` and compare the receiver's null-PIN behavior. Do not install for diagnosis.
3. **Design options only after gates:** (a) restore normal PIN UI routing for general devices, (b) owner-approved DS3-specific handler with authenticated enrollment and scoped device validation, or (c) vetted official OTA. Keep system signing/permissions and rollback in view.
4. **Safety:** no global Bluetooth security change, Bluetooth service restart, system APK overwrite, injection, or firmware flash without owner approval. Previous C4C-3 `NO_GO` still holds; wired DS3 operation was already confirmed.

## 8. Related research

- [Issue #6](https://github.com/franfran/android-bt-gamepad/issues/6) — investigation history
- [Draft PR #48](https://github.com/franfran/android-bt-gamepad/pull/48) — vendor TvSettings DEX evidence
- [Draft PR #47](https://github.com/franfran/android-bt-gamepad/pull/47) — earlier BTIF pairing policy investigation

No runtime modifications were made during this documentation work.

### Owner-confirmed firmware variant (2026-10-31)

Owner explicitly confirms this physical iMETBOX M3 was sold as the **International version (國際版)** by the Hong Kong seller at purchase. **Use only M3 International H618 2025-03-03** as the first offline firmware-comparison candidate; do not substitute Taiwan M3, M3 Pro, Pixel raven, or Tanix firmware. Seller designation supports regional selection but still does not prove hardware revision or flash compatibility. Comparison target is the newer package's `TvSettings.apk` and specifically `BluetoothPairingRequest.onReceive` / PIN variant behavior; **no OTA install authorized**. The official firmware index is https://imetbox.net/download.html . Current browsing can verify the listing, but has not retrieved an actual OTA archive (download links dynamically provided by site; sandbox download DNS failed). Do not claim a bytecode comparison or Bluetooth fix yet.

### Offline 2025 International firmware comparison — completed 2026-10-31

Owner downloaded the official-listing **M3 International H618** PhoenixSuit IMG named `h618_jjx_english_20250303-1532.img`, extracted `wty:super.fex` via `sunxi-fw`, split sparse dynamic-super image into `system_a`, `product_a`, `vendor_a`, and `vendor_dlkm_a`, and extracted the newer `TvSettings.apk` from the system image. Comparison of the owner-uploaded `m3-2025-extracted.zip` and earlier owner-pulled M3 installed APK `M3-TvSettings.apk.zip`:

| Artifact | Size (bytes) | SHA-256 |
|---|---:|---|
| Installed M3 2024 `TvSettings.apk` | 37,088,675 | `70d8fdd66f6b0bd3a06f30e4d755b709f2026955fda3955bff537840b15d2225` |
| M3 International 2025-03-03 firmware `TvSettings.apk` | 37,088,675 | `70d8fdd66f6b0bd3a06f30e4d755b709f2026955fda3955bff537840b15d2225` |

**Result: byte-for-byte identical.** The 2025 International firmware **does not update this TV Settings APK** and therefore does not repair the `onPair(variant,null)` PIN branch *in the APK itself*. This does **not** prove the complete Bluetooth stack is unchanged, nor that other components cannot alter runtime pairing behavior. Firmware build provenance is provided by owner file name and extraction; cryptographic OEM authenticity beyond the site's download provenance was not independently verified.

**Recommended next comparison** (offline, no flash): extract 2025 `Bluetooth.apk` and `framework.jar` if we want to check whether other components differ; don't claim entire firmware DS3 fix/no fix based solely on TvSettings byte identity.

### Offline 2025 International firmware Bluetooth stack comparison — completed 2026-10-31

Owner supplied `m3-2025-bluetooth-framework.zip`, with 2025 International firmware `Bluetooth.apk` and `framework.jar` extracted from `system_a.img`. Compared directly to owner-extracted installed 2024 artifacts `M3-Bluetooth.apk` and `M3-framework.jar` from `Archive(1).zip`.

| Artifact | 2024 installed | 2025 International | Result |
|---|---|---|---|
| `Bluetooth.apk` | 8,458,801 bytes; SHA256 `d12506341ffa2e733603a43bb9776b590d1fc3eb5c4655b13699cec4b58d7e0f` | 8,458,801 bytes; **same SHA256** | **Byte-identical**: Bluetooth APK service code was not updated |
| `framework.jar` | 35,001,576 bytes; SHA256 `90019f7ee656beaca72f87b7b1af574e56f58aea85911c7786410086ff565deb` | 35,001,828 bytes; SHA256 `2efb00d7bce5a9f5ef6d77fba25e701c7ae0fc18bdc71240e08be8e0e45c9bf4` | 252-byte increase, not byte-identical |
| `framework.jar` internal ZIP entries | 43 entries | same 43 entries | **Only `classes4.dex` differs**; all other entries including other classes DEX are byte-identical |

Parsed the old/new `classes4.dex` tables: the class set is identical (4029 class descriptors), and the code-item method signature set is identical (28614 methods with nonempty code). Only **five new strings** were observed (`android.intent.extra.TIME`, `android.intent.extra.ASSIST_INPUT_DEVICE_ID`, `persist.oranth.imtv`, `getEventTime`, `launchAssist`) and **two method references** (`KeyEvent.getEventTime()`, `SearchManager.launchAssist(Bundle)`); because the DEX string/method tables shift, a raw byte comparison of individual methods in `classes4.dex` exaggerates changes. This is **not** a source-level proof that no other code semantics changed.

The `BluetoothDevice` class is **not defined in `classes4.dex`**, so the byte-identical other DEX entries retain the previously verified `BluetoothDevice.setPin(String)` / `convertPinToBytes(String)` implementation. Combined with the previously confirmed identical `TvSettings.apk`, the **2025 International firmware contains no update to these three inspected pairing components' relevant logic** (TvSettings receiver, Bluetooth APK, framework BluetoothDevice PIN methods). **Do not conclude all possible driver/native modifications or runtime behavior are unchanged:** vendor libraries, boot/vbmeta, configuration and other partitions were not compared.

**Decision:** there is no observed pairing-handler fix in the 2025 International build's inspected Java components; flashing this image solely as a DS3 PIN bug fix is not justified by this evidence. Next research gate is the exact runtime pairing variant or a scoped fix design, with owner approval and rollback protections.
