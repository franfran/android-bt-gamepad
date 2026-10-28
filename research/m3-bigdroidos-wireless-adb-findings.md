# M3 TV Box — BigDroidOS Wireless ADB Findings and Setup

**Device:** M3 TV Box  
**OS:** Android 12 / BigDroidOS 2.0.1  
**Build:** `apollo_p1-userdebug 12 SP1A.211105.004 20240412.161509`  
**Verified LAN address during testing:** `192.0.2.10`  
**Status:** Wireless ADB auto-start confirmed across a reboot and fresh disconnect/reconnect (2026-10-24).

## Critical finding: use TCP port 1080, not 5555

**This firmware exposes its working network ADB service on TCP port `1080`, rather than the commonly used `5555`.** Use:

```bash
adb connect 192.0.2.10:1080
adb -s 192.0.2.10:1080 shell getprop ro.product.model
```

The observed runtime property was `service.adb.tcp.port=1080`, and ADB connectivity to port 1080 was successfully tested. Connection attempts to port 5555 were refused after reboot. We have **not** proven that 1080 is the factory-default port on every M3 or BigDroidOS installation; it is the **verified port for this box**. Its IP address may change unless reserved by DHCP.

## Root cause of ADB not starting after reboot

Developer Options / USB debugging was enabled, but `adbd` did not start automatically after reboot. The Android init configuration includes a vendor-specific control in:

`/vendor/etc/init/hw/init.oranth.rc`

```rc
# adb
on property:sys.boot_completed=1 && property:persist.vendor.adb.enabled=*
    setprop vendor.adb.enabled ${persist.vendor.adb.enabled}

on property:vendor.adb.enabled=1
    start adbd

on property:vendor.adb.enabled=0
    stop adbd
```

Before the fix, `persist.vendor.adb.enabled=0` and `vendor.adb.enabled=0`. The observed reboot state was `init.svc.adbd=stopped`. Manually running `start adbd` from a root terminal restored connectivity on port 1080, demonstrating that the obstacle was the vendor ADB service enablement rather than a need to switch to port 5555.

Android also defines `adbd` as a disabled, explicitly-triggered service in `/system/etc/init/hw/init.usb.rc`, so `class core` does not itself guarantee startup.

## Change applied to enable automatic ADB startup

Once connected on the working port, open an Android shell from the Mac:

```bash
adb -s 192.0.2.10:1080 shell
```

Inside the **TV Box shell**:

```sh
su
id                            # verify uid=0(root)
setprop persist.vendor.adb.enabled 1
getprop persist.vendor.adb.enabled
getprop vendor.adb.enabled
getprop init.svc.adbd
exit
exit
```

Observed values following the change:

```text
persist.vendor.adb.enabled = 1
vendor.adb.enabled         = 1
init.svc.adbd              = running
```

**No changes to `/system`, `/vendor`, `build.prop`, or init scripts were required.** The existing firmware's persistent vendor property is used to request ADB startup after boot completion.

## Reboot verification — passed

From the **Mac Terminal** (not inside `adb shell`):

```bash
adb -s 192.0.2.10:1080 reboot
```

After boot, a fresh connection was verified:

```bash
adb disconnect 192.0.2.10:1080
adb connect 192.0.2.10:1080
adb -s 192.0.2.10:1080 shell '
  echo "===== DEVICE ====="
  getprop ro.product.model
  echo "===== ADB ====="
  getprop init.svc.adbd
  getprop persist.vendor.adb.enabled
  getprop vendor.adb.enabled
  getprop service.adb.tcp.port
'
```

Actual recorded output:

```text
disconnected 192.0.2.10:1080
connected to 192.0.2.10:1080
===== DEVICE =====
M3
===== ADB =====
running
1
1
1080
```

**Result:** Wireless ADB was verified to start after reboot and was available from the Mac without reopening the TV Box terminal app.

## Why `persist.adb.tcp.port=5555` was not the solution

Earlier troubleshooting set:

```sh
setprop persist.adb.tcp.port 5555
```

That value survived reboot, but the TV Box still used `service.adb.tcp.port=1080` when `adbd` was running. Attempts to connect to 5555 were refused. Setting `persist.adb.tcp.port` did **not** enable the daemon at boot; changing `persist.vendor.adb.enabled` did.

At the time of final verification, the earlier test property `persist.adb.tcp.port=5555` was still present. It was **not** changed to 1080, and there is no recorded successful cleanup of that property. Because the verified configuration currently works, avoid making further changes just to normalize the port unless there is a reason and a fresh verification plan.

## Day-to-day use

From the Mac:

```bash
adb connect 192.0.2.10:1080
adb devices -l
```

If unavailable, verify the box is fully booted, the LAN IP is unchanged, and port **1080** is reachable. Then check the vendor enablement and daemon state from the local terminal if required:

```sh
su
getprop persist.vendor.adb.enabled
getprop vendor.adb.enabled
getprop init.svc.adbd
getprop service.adb.tcp.port
```

For one-session manual recovery (root shell):

```sh
start adbd
```

## Optional: disable always-on ADB

**Security warning:** The collected properties included `ro.adb.secure=0`, and the TV Box permits a root shell with SELinux reported as permissive. Network ADB can therefore present substantial risk to anyone sharing the LAN. Do not expose TCP port 1080 to the internet or untrusted networks. Prefer a restricted management VLAN or disable when not needed.

To disable the vendor auto-start setting from a **root shell**:

```sh
setprop persist.vendor.adb.enabled 0
setprop vendor.adb.enabled 0
```

The second command invokes the firmware's `stop adbd` trigger and will terminate the current ADB connection. Re-enable it locally from the TV Box terminal if required:

```sh
su
setprop persist.vendor.adb.enabled 1
setprop vendor.adb.enabled 1
```

For this model, use **1080** for the next wireless connection unless a new inspection proves the port has changed.

## Evidence and confidence

- **Confirmed by supplied init file:** `/vendor/etc/init/hw/init.oranth.rc` has the `persist.vendor.adb.enabled` → `vendor.adb.enabled` → `start/stop adbd` logic.
- **Confirmed by supplied property dump:** `persist.vendor.adb.enabled=0`, `vendor.adb.enabled=0`, `service.adb.tcp.port=1080`, `persist.adb.tcp.port=5555`, `ro.adb.secure=0` before the successful change.
- **Confirmed by live user test:** setting `persist.vendor.adb.enabled=1`, rebooting, disconnecting, and reconnecting to `192.0.2.10:1080` worked; `adbd=running` and both vendor enable flags were `1`.
- **Not established:** Whether 1080 is the factory-default port for every BigDroidOS box, or whether the legacy persistent 5555 setting can be safely removed without altering any other firmware behavior.

*Scope: hardware-management access documentation only. No subtitle project runtime or application changes.*
