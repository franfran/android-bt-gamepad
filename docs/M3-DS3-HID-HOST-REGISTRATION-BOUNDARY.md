# Android 12 HID Host registration — source-matched pre-auth boundary

**Offline 2026-10-31.** Original-M3 S8 evidence + AOSP source comparison, **not** proof of an OEM callback.

## Source matched

The relevant profile is **HID Host** `stack/hid/hidh_conn.cc`, **not** `hidd_conn.cc` HID Device. AOSP's Host `hidh_conn_reg()` creates `tL2CAP_APPL_INFO` callback table `hst_reg_info` including `hidh_l2cif_connect_ind` and registers both PSM 0x11 and 0x13 using `L2CA_Register2(..., BTA_SEC_AUTHENTICATE | BTA_SEC_ENCRYPT)` (see AOSP hidh_conn.cc commit 4456dc7c91e1cfe2dd0cfd9154274a573d156b03). The owner's exact M3 libbluetooth.so separately shows `hidh_conn_reg` calling `L2CA_Register2` twice and security mask 0x36.

`tL2CAP_APPL_INFO` callback table is an **internal statically registered profile callback**, not a documented runtime third-party plugin API. By the time `hidh_l2cif_connect_ind` runs, the L2CAP/BTM security requirement may already have been evaluated; attaching only to this callback is not proof of a viable pre-auth cable-pairing fix.

Crucially, changing `hidh_conn_reg`'s `BTA_SEC_AUTHENTICATE|BTA_SEC_ENCRYPT` registration changes the **service-wide HID listening security**, affecting all remote peers; it is not a DS3-only decision. BlueZ 5.83 employs a broad early low-security listen with a later cable-device check, but that architecture must not be blindly copied onto Android, particularly because of spoofed controller identities and keyboard-like input attacks.

## Consequence for implementation

**No simple Android public plugin callback** has been shown. The verified S8 `l2c_csm_execute` (incoming peer+PSM) is the *narrower contextual evaluation point*, but it is internal native stack code and does not demonstrate safe plugin interception. Therefore S7 `dlopen` alone cannot solve the problem.

## Candidate gates

- **Do not use** `BluetoothHidDevice.registerApp()` on M3: API is peripheral-role and disables HID Host while registered (confirmed Android 12 reference).
- **Do not modify globally** `L2CA_Register2` security mask for all HID controllers in a deployable design.
- **Do not hook `hidh_l2cif_connect_ind` assuming it precedes auth:** verify exact event ordering first.
- A scoped OEM source patch could in principle add a decision before Classic BTM security with peer/PSM context, but exact target source/ABI/packaging and Java HID Host gate are separate unverified deployment requirements.
- Runtime native `.so` / S7 loader route remains design-only under C4C-3 NO_GO; no live injection, system patch, pairing attempt or service restart approved.

## Sources
- https://android.googlesource.com/platform/system/bt/+/4456dc7c91e1cfe2dd0cfd9154274a573d156b03/stack/hid/hidh_conn.cc
- https://android.googlesource.com/platform/frameworks/base/+/android12-release/core/java/android/bluetooth/BluetoothHidDevice.java
- S8 PRs #26/#32/#38; current Draft PR #50.
