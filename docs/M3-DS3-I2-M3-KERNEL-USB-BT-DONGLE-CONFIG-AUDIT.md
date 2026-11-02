> **DEFERRED / HISTORICAL (Owner 2026-11-02).** The original recovered M3 kernel evidence below remains valid, but USB dongle feasibility and kernel/host inventory are **not current PR #52 tasks**. Return to it only in a separate future dongle PR after the plugin route's final determination. Current focus: [OEM plugin-only audit](M3-DS3-I1-PLUGIN-ONLY-ACCEPTANCE-AND-OEM-ABI-AUDIT.md).

# I2 — M3 kernel configuration: dedicated USB Bluetooth dongle feasibility

**Evidence:** Read-only analysis of the Owner's previously uploaded `m3-kernel.config(1).gz` (31,530 bytes compressed, 141,529 bytes text, 5,295 lines). This is **the M3 configuration upload**, not a public H618 BSP default defconfig and not a live module inventory.

**Uploaded gzip SHA-256:** `403e16be17169036dee77c1ba93b06f085b3f4a9376f7b51205a08e4a71410c7`.

## Exact configuration evidence

```text
CONFIG_BT=y
CONFIG_BT_BREDR=y
CONFIG_BT_HIDP=y
# CONFIG_BT_HCIBTUSB is not set
# CONFIG_BT_HCIUART is not set
# CONFIG_BT_HCIBTSDIO is not set
# CONFIG_BT_HCIBCM203X is not set
# CONFIG_BT_HCIBPA10X is not set
# CONFIG_BT_HCIBFUSB is not set
# CONFIG_BT_HCIVHCI is not set

CONFIG_USB_SUPPORT=y
CONFIG_USB=y
CONFIG_USB_EHCI_HCD=y
CONFIG_USB_OHCI_HCD=y
# CONFIG_USB_XHCI_HCD is not set
CONFIG_USB_EHCI_HCD_SUNXI=m
CONFIG_USB_OHCI_HCD_SUNXI=m
CONFIG_USB_SUNXI_HCD=m
CONFIG_USB_SUNXI_HCI=m
CONFIG_USB_SUNXI_EHCI0=m
CONFIG_USB_SUNXI_EHCI1=m
CONFIG_USB_SUNXI_EHCI2=m
CONFIG_USB_SUNXI_EHCI3=m
CONFIG_USB_SUNXI_OHCI0=m
CONFIG_USB_SUNXI_OHCI1=m
CONFIG_USB_SUNXI_OHCI2=m
CONFIG_USB_SUNXI_OHCI3=m
# CONFIG_USB_OTG is not set
CONFIG_USB_ROLE_SWITCH=y
CONFIG_USB_HID=y
CONFIG_USB_STORAGE=y
CONFIG_MODULES=y
CONFIG_MODVERSIONS=y
CONFIG_MODULE_UNLOAD=y
# CONFIG_USB_MON is not set

CONFIG_UHID=y
CONFIG_INPUT_UINPUT=y
CONFIG_HID_SONY=y
```

## Architecture B (separate USB dongle / standalone daemon) — initial decision

**Not plug-and-play through the conventional kernel Bluetooth stack:** `CONFIG_BT_HCIBTUSB` is disabled. A typical dongle cannot be assumed to bind to `btusb` or appear as kernel HCI device `hci1`. This is a direct result from the uploaded kernel config, NOT a live-dongle test.

**Physical USB Host may work, not yet established from config alone:** EHCI/OHCI are present, and SUNXI host-specific pieces are configured as modules. Whether those `.ko` files exist in vendor partitions, are actually loaded, and support the intended M3 USB Host port must be verified separately. The enabled `USB_HID` and `USB_STORAGE` symbols are not proof that a particular USB dongle enumerates.

**Possible alternative research (CONDITIONAL):** A standalone daemon might use userspace usbfs/libusb directly to a dedicated USB Bluetooth dongle, avoiding `btusb` kernel ownership. But it would need a genuine controller command/event + ACL transport, Bluetooth Classic host stack, authentication/link-key/legacy DS3 compatibility and exclusive USB interface access. This config does not demonstrate that any of those prerequisites work. This must not interfere with OEM Fluoride's internal controller.

**Do not assume the OEM controller is handled by Linux `HCIUART`:** `CONFIG_BT_HCIUART` is also disabled. A vendor Bluetooth transport, vendor user-space interface, or other mechanism may be used. The literal Android/OEM implementation must be inspected; calling the OEM controller UART is a hypothesis until proven.

**Input output bridge:** Kernel `CONFIG_UHID=y` and `CONFIG_INPUT_UINPUT=y` show those interfaces compiled in; device nodes, privileges, Android InputReader recognition and actual DS3 input still require verification. These are downstream of obtaining an authentic Bluetooth link.

## Scope / safety

This document is **only** an offline audit of an Owner-provided config. No device, USB, module, Bluetooth controller, root, or runtime commands were executed. No raw proprietary binary, MAC/keys, private logs or original config uploaded to public GitHub.

**Next PR #52 activity:** update Architecture B feasibility to **CONDITIONAL (kernel btusb route NO_GO as configured)**. Continue investigating separate USB dongle *userspace* ownership and exact USB Host functionality, plus Architecture A supported plugin hooks and D supported APIs. No full Android BSP required just to examine these routes; PR #51 build workstream remains separate. For a live validation, require separate Owner-approved read-only plan.

**Do not infer** that a kernel module could trivially be loaded from stock ROM; the required matching kernel build, signing/SELinux, dependencies and original kernel ABI have not been assessed. No kernel changes or loading authorized.
