# RetroBox DS3 Bluetooth Stage 1 — conservative L2CAP bind probe

Validated on host: ELF32 ARM EABI5 statically linked, no Android NDK/libc required. **Not yet executed on M3**.

Run:

```sh
DEVICE=192.0.2.10:1080
adb -s "$DEVICE" push l2cap_bind_probe_static /data/local/tmp/
adb -s "$DEVICE" shell su 0 chmod 755 /data/local/tmp/l2cap_bind_probe_static
adb -s "$DEVICE" shell su 0 /data/local/tmp/l2cap_bind_probe_static
```

The binary creates an AF_BLUETOOTH L2CAP SOCK_SEQPACKET socket and calls bind() on **test PSM 0x1001**. It does not use DS3 HID PSM 0x11/0x13, listen(), connect(), Bluetooth HCI, keys or configuration. The socket is closed immediately. Success only proves local bind support, not wireless connectivity or compatibility with Android's Bluetooth stack. If busy/error, it prints the Linux errno.

Source included for audit. No libc and no NDK. ARM EABI Linux syscall numbers: socket=281, bind=282, close=6, write=4, exit=1. Compiled with clang/lld as 32-bit ARM static executable.
