# I2/I6 — USB cable enrollment transaction: BlueZ reference, offline DS3 model

**Status:** Host-only C++17 transaction / approval model; **not** a M3 USB driver, Bluetooth security exception, Java integration or persisted trusted device. Draft PR #52 only; PR #50 and PR #51 remain independent.

## Proven references vs assumptions

### Existing RetroBox hardware evidence

The existing [project status](../STATUS.md) already reports **DS3 working over USB in RetroArch**, and a prior `sixpair` operation writing the M3 master Bluetooth address via USB. Following a PS-button attempt, the **M3 Bluetooth stack** proceeded through a PIN request but HCI authentication ultimately timed out with `0x22`; `BOND_BONDING` returned to `BOND_NONE`. Repeating USB setup or guessing PIN is **not** a proven solution.

### External public source reference: Linux BlueZ `sixaxis` plugin

Pinned public reference: [BlueZ `plugins/sixaxis.c` at commit a93047cd](https://kernel.googlesource.com/pub/scm/bluetooth/bluez.git/+/a93047cd044fb17d687f43bef95289ec834876b2/plugins/sixaxis.c).

- [`sixaxis_get_device_bdaddr`](https://kernel.googlesource.com/pub/scm/bluetooth/bluez.git/+/a93047cd044fb17d687f43bef95289ec834876b2/plugins/sixaxis.c#98) reads **USB feature report 0xF2**, 18 bytes, with the device's 6-byte address at byte offset 4 (BlueZ reverses byte order via `baswap`).
- [`sixaxis_get_central_bdaddr` / `sixaxis_set_central_bdaddr`](https://kernel.googlesource.com/pub/scm/bluetooth/bluez.git/+/a93047cd044fb17d687f43bef95289ec834876b2/plugins/sixaxis.c#150) reads/writes **USB feature report 0xF5**, 8 bytes, with host 6-byte address at offset 2, byte-reversed; the SET buffer includes `0xF5, 0x01`.
- [`setup_device` and `agent_auth_cb`](https://kernel.googlesource.com/pub/scm/bluetooth/bluez.git/+/a93047cd044fb17d687f43bef95289ec834876b2/plugins/sixaxis.c#274) use a **cable authorization callback** prior to configuring the USB controller's host address, and maintain/removal of a temporary Bluetooth device record. The current BlueZ file also handles USB unplug cancellation and keeps cable pairing as dedicated state.
- BlueZ is **not Android Fluoride**: it uses BlueZ agent, HIDraw, Udev, device database and input server APIs. Neither the plugin nor its GNU GPL source can be copied directly into H618 without a separate architecture and license review. The C++ code below is original host-only implementation using report format and sequence **concepts**, not a code port.

## New original C++17 implementation

Files:
- `experiments/m3-ds3-cable-session/usb_enrollment.h`
- `experiments/m3-ds3-cable-session/test_usb_enrollment.cc`

State machine: `Idle → AwaitOwner → AwaitWrite → AwaitReadback → Committed`, or `Idle → AwaitOwner → AwaitReadback → Committed` if controller's stored host already equals desired host. Any refusal, failed write/readback, untrusted USB source, wrong VID/PID or cable removal before commit is rejected/cancelled. Changing M3 adapter address cancels the committed record.

The model parses **exactly 18 bytes for F2** and **exactly 8 for F5**, with BlueZ-compatible 6-byte offset/endianness, and constructs (does not send) the 8-byte F5 write payload. It models cable disconnect before/after successful enrollment. **No physical USB read/write happens in any test.**

**Critical distinction:** `trusted_usb_transport` is an **unproven external Boolean** placeholder for a future privileged local USB backend, and `OwnerDecision(true)` is not a real Android consent UI. VID/PID and USB reports are not cryptographic attestation. Neither successful F5 readback nor a later matching radio MAC proves the Bluetooth peer's identity. Accordingly `CheckRadioAddress` can return only **`kAddressCandidateNotAuthenticated`**, never a grant to bypass BTM, spoof LinkKeys, set `BOND_BONDED`, create UHID or ignore Java `okToConnect`. No host MAC, physical DS3 serial/key, real PIN or raw snoop is committed; tests use synthetic addresses only.

**Defense-in-depth added in this model:** After an apparently successful USB F5 SET, require a fresh F5 **readback matching the intended adapter** before recording candidate enrollment. The referenced BlueZ callback reads the old central address and conditionally writes the new one; it does not itself demonstrate a post-write readback. This readback requirement is our **proposed validation improvement**, not a claim that BlueZ implements it.

## Host verification (actual execution)

GCC 14.2.0 in isolated Linux host, strict C++17 and sanitizers:

```text
g++ -std=c++17 -Wall -Wextra -Werror -pedantic test_usb_enrollment.cc -o usb_test
./usb_test
47/47 PASS (host-only USB enrollment transaction)

g++ -std=c++17 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer test_usb_enrollment.cc -o usb_test_san
ASAN_OPTIONS=detect_leaks=1 ./usb_test_san
47/47 PASS (host-only USB enrollment transaction)
```

These are 47 assertions in one executable, **not 47 independent integration or security tests**. Test cases cover report sizes/IDs, byte reversal, USB source and Sony VID/PID checks, missing owner approval, write failure, mismatched readback, cable pull before commit, adapter address change, committed address-candidate-only behavior and invalid F2 address. The existing `run_cpp_host_tests.sh` has been updated with the C++ test invocation.

In the same local session, the previous PR #52 `RequestRefPool` model was also reconstructed from its exact GitHub content and rerun with GCC + AddressSanitizer/UBSan: **92/92 PASS on both**. This is the old request-ref model, **not** proof the source overlay compiles into Android.

## Device-facing work remains NO_GO

An eventual enrollment implementation would need:
1. A trusted **M3-local USB device observer and Feature Report I/O**. Determine appropriate Android USB/HID access and privileges before any hardware writes. Do not accept self-reported Bluetooth VID/PID or an app-supplied “USB present” bit as proof.
2. A real **owner consent workflow** with error handling, USB attach lifetime, bounded/atomic persistence of the enrolled device/adapter pairing, and revocation. The existing manual `sixpair` step may have already programmed the correct host, so prioritize an **offline/read-only** provenance inspection before any reprogramming. Avoid raw MACs in PR logs.
3. Integration of enrollment candidate into a narrowly scoped, event-bound Native↔Java admission path. A MAC match is **candidate discovery only**, never a Bluetooth authentication bypass or direct UHID approval.
4. Actual Sony DS3 controller proof / bounded security decision (if any), safe BTM/L2CAP callback lifetime, Java admission, descriptor/input report validation and full source build. These are still unresolved.
5. Independent M3 recovery, explicit owner authorization and a supervised one-shot plan for any actual target changes; current safety posture remains NO_GO.

**Decision:** external source reference and offline USB F2/F5 transaction representation PASS; real USB enrollment backend, secure radio identity and DS3 wireless connection NOT IMPLEMENTED.
