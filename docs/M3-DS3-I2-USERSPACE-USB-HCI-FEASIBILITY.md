# PR #52 I2 — M3 userspace USB Bluetooth HCI: independent controller feasibility

**Date:** 2026-11-02. **Scope:** Architecture B2 research only; no M3 USB/BT access, no module loads, no daemon, no new library injected, no full BSP. PR #52 remains Draft. PR #50 reverse engineering and PR #51 OEM source-modification workstreams remain separate.

## Owner's recovered kernel configuration is authoritative (no need to ask for it again)

Read [actual M3 kernel audit](M3-DS3-I2-M3-KERNEL-USB-BT-DONGLE-CONFIG-AUDIT.md) based on previously supplied `m3-kernel.config(1).gz`, SHA-256 `403e16be17169036dee77c1ba93b06f085b3f4a9376f7b51205a08e4a71410c7`.

**PROVEN configuration flags:** `CONFIG_BT=y`, `CONFIG_BT_BREDR=y`, **`# CONFIG_BT_HCIBTUSB is not set`**, **`# CONFIG_BT_HCIUART is not set`**, `CONFIG_USB=y`, EHCI/OHCI core `=y`, SUNXI USB host variants `=m`, `CONFIG_MODULES=y`, `CONFIG_UHID=y`, `CONFIG_INPUT_UINPUT=y`. `CONFIG_USB_OTG` not set; fixed USB Host ports are not thereby disproved.

**Consequences:**
- **NO_GO:** assuming a conventional kernel `btusb` Bluetooth HCI device appears as `hci1`. No `btusb` driver is configured.
- **CONDITIONAL:** Linux USB core/Host Controller and usbfs can give a *separate USB dongle* directly to a userspace process. The absence of kernel `btusb` is not itself a reason to reject userspace USB requests. **Important existing M3 hardware result:** the Owner already successfully played DS3 via a wired USB connection in RetroArch (see [`docs/STATUS.md`](STATUS.md)), so at least one USB Host + USB HID path has operated on M3. This **does not** prove that a Bluetooth dongle enumerates, that all SUNXI modules are currently loaded, that usbfs nodes/permissions exist, or that USB HCI can be used from an APK/daemon.
- **Do not confuse internal controller:** prior M3 observations associate its existing Bluetooth service with OEM Android HCI HAL and vendor AIC UART path. `CONFIG_BT_HCIUART=n` is consistent with no Linux standard HCIUART driver; it does **not** prove how proprietary HAL is implemented. The built-in controller is **not** an Android `UsbDevice` that `libusb` can automatically take over.

## Why an additional dongle? Controller ownership, not missing Bluetooth capability

```text
CURRENT (remains unchanged):             B2 hypothetical, separate dongle:
M3 built-in radio                        USB dongle (separate HCI radio)
      |                                            |
OEM HCI HAL / vendor path                   USB Host -> usbfs / libusb
      |                                            |
OEM Fluoride stack                          standalone userspace Classic stack
      |                                            |
normal Android Bluetooth                    DS3 BR/EDR HID PSM 0x11/0x13
                                                   |
                                              UHID/uinput -> Android -> RetroArch
```

**PROVEN from prior PR #52 source audit:** OEM Fluoride registers fixed HID PSM 0x11/0x13, and a competing Classic socket registration can overwrite `L2CA_Register` PSM callback table. A second HCI host cannot safely arbitrate the OEM controller merely because root exists. Same-controller B remains **NO_GO** without a supported HCI/PSM broker; userspace libusb does NOT solve that because the existing OEM radio has no demonstrated exposed USB HCI interface. B2 would avoid *that specific ownership conflict* by being the single host of a physically distinct controller. The extra dongle is an **optional fallback research hypothesis**, not a user requirement or a recommendation to purchase hardware.

## Actual public implementation evidence: an independent USB HCI host stack exists

- **PROVEN standard:** [Bluetooth SIG USB Transport Layer](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core_v6.3/out/en/host-controller-interface/usb-transport-layer.html) defines Bluetooth USB HCI via **control** transfers for HCI commands, **interrupt IN** for events, **bulk IN/OUT** for ACL, and separate **isochronous** endpoints for voice. Class/subclass/protocol `0xe0/0x01/0x01` is defined. Do **not** hardcode recommended endpoint *addresses*; parse real interface descriptors. See [USB-IF class codes](https://usb.org/defined-class-codes).
- **PROVEN Android userspace API:** [Android UsbDeviceConnection](https://developer.android.com/reference/android/hardware/usb/UsbDeviceConnection) exposes `claimInterface`, `controlTransfer`, `bulkTransfer`, `getFileDescriptor`, and `close`; [Android USB Host guide](https://developer.android.com/develop/connectivity/usb/host) requires Host functionality and USB device permission. This API is for a physically enumerated USB device, NOT Android's existing virtual Bluetooth HAL.
- **PROVEN libusb Android integration:** [libusb Android README](https://github.com/libusb/libusb/blob/987c1170d0018ba82557823a98ae443e8335e11b/android/README#runtime-permissions) shows `UsbManager.openDevice` -> `UsbDeviceConnection.getFileDescriptor()` -> `libusb_wrap_sys_device`, with `LIBUSB_OPTION_NO_DEVICE_DISCOVERY` for Android. It documents an Android-native JNI bridge; the developer must keep the Java connection alive and manage FD/close/permission lifecycle. [libusb Android wiki](https://github.com/libusb/libusb/wiki/Android) explicitly conditions support on Host support + permissions. This is not proof M3 can grant permissions.
- **PROVEN existing independent Classic stack:** [BlueKitchen BTstack README](https://github.com/bluekitchen/btstack/blob/9edb5d82ea6ec4466a393415d65030929330acdf/README.md) lists H2 USB HCI and Classic support. Its [libusb port](https://github.com/bluekitchen/btstack/blob/9edb5d82ea6ec4466a393415d65030929330acdf/port/libusb/README.md) is demonstrated on POSIX using a *dedicated* USB dongle. [HCI libusb implementation](https://github.com/bluekitchen/btstack/blob/9edb5d82ea6ec4466a393415d65030929330acdf/platform/libusb/hci_transport_h2_libusb.c) uses `libusb_get_device_list/open/claim_interface`, parses endpoints and submits asynchronous transfer callbacks; [Classic HID Host demo](https://github.com/bluekitchen/btstack/blob/9edb5d82ea6ec4466a393415d65030929330acdf/example/hid_host_demo.c) receives incoming HID sessions and reports. Source pin: `bluekitchen/btstack@9edb5d82ea6ec4466a393415d65030929330acdf` (2026-10-30).
- **CRITICAL adaptation:** Stock BTstack `usb_open` scans USB devices (`hci_transport_h2_libusb.c:1071-1165`), and `prepare_device` may detach a kernel driver, reconfigure, reset or claim interface (`835-955`). It **does not** use Android's pre-authorized wrapped FD out of the box. **Never execute the unmodified POSIX sample on M3**. A future Android transport must accept an explicitly selected, permitted, externally opened USB handle, disable auto-enumeration/auto-reset/detach, avoid kernel driver interference, only claim the dedicated dongle interface when specifically authorized, and fail closed.
- **CRITICAL authentication:** [BTstack HID Host demo lines 331-335](https://github.com/bluekitchen/btstack/blob/9edb5d82ea6ec4466a393415d65030929330acdf/example/hid_host_demo.c#L331-L335) explicitly **rejects legacy PIN requests** with `gap_pin_code_negative`. Consequently a generic BTstack HID Host demo is *not* a DS3 compatibility fix. Need genuine DS3 legacy authentication behavior, USB-enrollment provenance, link/pairing persistence, and response to Sony HID feature SET_REPORT requirements. Historic M3 HCI status 0x22 was an LMP response timeout; it is not automatically solved by switching to BTstack.
- **License:** [BTstack LICENSE](https://github.com/bluekitchen/btstack/blob/9edb5d82ea6ec4466a393415d65030929330acdf/LICENSE) permits personal/noncommercial use subject to conditions; commercial/monetary distribution requires separate licensing inquiry. Do not copy BTstack code into this repository without review. libusb licensing is separate.

## Offline, removable PoC: descriptor-only preflight (now implemented)

The [offline Python gate](../experiments/m3-ds3-compat-adapter/usb_hci_descriptor_gate.py) accepts **only** a sanitized JSON object with a list of USB `interfaces`: per interface `number`, `alternate`, `class`, `subclass`, `protocol` and endpoint `address`/`type`. It checks exactly one standard Bluetooth HCI alt-0 interface, and a required interrupt-IN plus bulk-IN and bulk-OUT path. It **does not** access USB/device sysfs, scan real devices, take root, return addresses, use HCI or create Android input. It intentionally emits `DESCRIPTOR_CANDIDATE_ONLY`, never `GO` or `DS3_SUPPORTED`. Unknown vendor-specific USB protocols fail closed pending separate evidence. Endpoint address examples in the SIG are **not required exact values**.

Use a **synthetic** fixture offline:

```json
{
  "interfaces": [
    {
      "number": 0, "alternate": 0, "class": 224, "subclass": 1, "protocol": 1,
      "endpoints": [
        {"address": 131, "type": "interrupt"},
        {"address": 132, "type": "bulk"},
        {"address": 5, "type": "bulk"}
      ]
    }
  ]
}
```

Reproduce with `python3 experiments/m3-ds3-compat-adapter/usb_hci_descriptor_gate.py /path/to/synthetic.json`. Host-only synthetic regression tests: `python3 -m unittest discover -s experiments/m3-ds3-compat-adapter -p test_usb_hci_descriptor_gate.py -v`. No hardware and no full Android BSP required.

**This is a negative-gate design fixture, NOT enumeration of any actual M3-connected dongle.** It does not prove `UsbManager` works or that userspace can open the interface.

## Decision gates / minimum approvals (do NOT bypass)

| Gate | Evidence needed | Status | Stop condition |
| --- | --- | --- | --- |
| B2-0 kernel configuration | Exact Owner config `btusb=n`, USB Host symbols, UHID/uinput | **PROVEN config** | No claim of working Host modules |
| B2-1 read-only M3 Host inventory | Build on the already-proven wired USB DS3 input; check dongle-specific enumeration and SUNXI module presence/load state, Android `UsbManager` Host feature and usbfs device nodes; redact USB serial/device identifiers | **PARTIAL: wired DS3 Host success PROVEN; dongle/usbfs UNTESTED, Owner-approved only** | No USB dongle enumeration/usable usbfs route -> NO_GO |
| B2-2 descriptor evidence | Inspect descriptors of an **independent USB Bluetooth dongle** (if owner has one), apply descriptor gate; no interface claim or USB writes | **UNTESTED** | No suitable or manufacturer-documented HCI USB transport -> NO_GO |
| B2-3 authorized exclusive USB device | Grant USB permission through Android app, wrap the device's FD; later, separately approved interface claim, no automatic detach/reset; avoid OEM radio | **UNTESTED** | Cannot obtain owned, stable handle without system/AVB changes -> NO_GO |
| B2-4 non-DS3 HCI transport smoke | After fresh authorization, read only controller HCI version/features through **dedicated** USB dongle; confirm event/ACL endpoint handling and genuine HCI callbacks | **UNTESTED / device operation** | Missing firmware/USB transport/claim stability -> NO_GO |
| B2-5 DS3 compatibility | Enroll DS3 over USB once to **dongle's address**, establish honest Classic link/legacy security, then PSM 0x11/0x13, supported descriptor and Sony initialization; prove reconnect on PS | **UNTESTED** | No legitimate DS3 pairing or stable inbound HID -> NO_GO |
| B2-6 input + boot lifecycle | Only after B2-5: UHID/uinput, normal Android gamepad, RetroArch, disconnection/reboot; no per-boot user prompt | **UNTESTED** | Requires repeated manual intervention -> unacceptable UX |

### Initial safest live inventory (not executed, do not run without Owner scope approval)

A separately reviewed **read-only** inspection should collect *redacted facts*, not raw identifiers: whether physical USB Host port exists and works with already accepted peripherals; `/sys/bus/usb/devices` existence and descriptor *shape only*, `/dev/bus/usb` existence, loaded SUNXI USB host drivers, Android `android.hardware.usb.host` feature, ownership/permissions on USB nodes. Never save raw USB serial numbers, device or adapter MACs, pairing data, or unfiltered system logs in GitHub. Do not load modules, unbind interfaces, claim PSM 0x11/0x13, start Bluetooth pairing, or reset internal Bluetooth.

## Workstream choice

- **B0 (M3 existing controller):** ideal one-radio UX, but userspace USB cannot discover the onboard vendor HAL as a USB dongle. Supported same-controller HCI/PSM delegation still **NO_GO** under present OEM evidence, not mathematically impossible.
- **B2 (dedicated userspace USB HCI):** independent low-level transport implementation now **source-grounded, CONDITIONAL** pending actual M3 USB Host/permissions and Android libusb port; **not** plug-and-play. Greater hardware/maintenance burden, but no `libbluetooth.so` replacement, and potential physical rollback by unplugging dongle.
- **C:** fallback native source integration requires new explicit Owner decision. Do not start a full BSP or modify OEM Bluetooth on PR #52.

**Safety:** No M3 operation or modification performed. No USB interface claimed, driver detached, firmware loaded, Bluetooth restarted, pairing attempted, or input events injected. PR #52 Draft, #50/#51 separate and untouched.

## Executed offline-only CI (2026-11-02)

[GitHub Actions run 41463143830](https://github.com/franfran/android-bt-gamepad/actions/runs/41463143830) completed **SUCCESS** on commit `5fbc627033a40aa43bae12c202d972107edc4538`; decoded logs explicitly show **`Ran 14 tests` and `OK`** for the exact committed Python gate/test files. No actual M3 USB device has been enumerated. Passed assertions cover descriptor shape, alternative endpoints, absent/mismatched interface, missing/bad endpoints, duplicate, alternate setting, multiple candidates, non-HCI device coexistence, sanitizer rejection and CLI privacy.

**Physical enrollment consequence:** existing sixpair enrollment targets the **onboard OEM Bluetooth controller**. If a *different* USB dongle becomes the DS3 host, the DS3 must be enrolled over USB *again*, using the second dongle's host address. Never overwrite the controller address blindly, post real addresses or claim a re-enrolled DS3 should automatically connect to both hosts.
