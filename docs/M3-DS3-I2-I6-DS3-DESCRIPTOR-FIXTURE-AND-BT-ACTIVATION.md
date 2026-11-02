# I2/I6 — DS3 USB vs Bluetooth HID descriptor evidence and activation gate

**Scope:** source/evidence reconciliation; no device operation, guessed report whitelist, or security patch. Relevant prior findings are in PR #50 `docs/M3-DS3-BLUETOOTH-OPERATIONAL-MODE.md` and `docs/M3-DS3-DUAL-CHANNEL-VALIDATION.md`.

## Known from this repository
- Owner demonstrated **wired USB Sony DS3 input working in RetroArch**, with archived USB `dumpsys input` showing Sony joystick and motion-sensor input for USB VID:PID `054c:0268`. This is not a Bluetooth report descriptor capture.
- The owner accepts **one-time USB enrollment**, then everyday Bluetooth wireless input without cable.
- PR #50 reviewed Linux `hid-sony.c`: Bluetooth DS3 operational initialization involves Feature SET_REPORT **`0xF4`** with `F4 42 03 00 00`; USB activation uses GET_REPORT `0xF2`. This is an *upstream source reference*, not proof of exact M3 kernel Bluetooth binding or a requirement to inject an extra report.
- Older offline readiness simulation differentiated device registration from **actual valid wireless input observed over built-in Bluetooth**. USB PASS cannot substitute for the latter.
- We have **not** located an owner-supplied verified Bluetooth HID report descriptor and matching wireless report stream. Do not infer it from USB VID:PID, controller name or `dumpsys input`.

## Two separate kernel-facing sources and proposed gates
Pinned H618 tree: `BPI-SINOVOIP/BPI-H618-Android12@250eabfc529518b7f26432663ed0a867ab2f625d`.

1. [`bta_hh_co_send_hid_info`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L506-L539) creates `UHID_CREATE` using descriptor from Bluetooth HID profile; upstream descriptor and reported VID/PID cannot by themselves prove radio identity. **Validate descriptor structure/capabilities before creating the kernel input device.**
2. [`bta_hh_co_write`](https://github.com/BPI-SINOVOIP/BPI-H618-Android12/blob/250eabfc529518b7f26432663ed0a867ab2f625d/system/bt/btif/co/bta_hh_co.cc#L292-L305) creates `UHID_INPUT` with a size check, not DS3 semantic validation. **Validate report according to trusted, separately reviewed Bluetooth descriptor and current native epoch before kernel delivery.**

The actual source path and order must also account for Sony Bluetooth **feature report operational initialization**, and `UHID_SET_REPORT` completion identified in PR #51. Descriptor validation, UHID creation, initialization and real input are distinct acceptance gates.

## Explicit unknowns — do NOT invent values
- Exact owner M3 DS3 **Bluetooth** HID report descriptor bytes, descriptor hash and top-level usages.
- Legitimate Bluetooth report IDs and maximum/minimum report sizes *as seen through this Fluoride path*, including packet-header stripping.
- Whether the M3 kernel `hid-sony` is enabled and automatically issues DS3 Bluetooth Feature 0xF4 after UHID creation.
- Whether Sony report mappings/quirks cause the kernel to present capabilities different from the raw Bluetooth descriptor.
- Whether the actual Bluetooth device needs its descriptor validated verbatim, normalized against Linux Sony quirks, or matched against trusted USB physical enrollment. Do not assume the USB descriptor is byte-identical to Bluetooth.
- Whether source-integrated filtering can be placed before **all** paths to `UHID_CREATE` and `UHID_INPUT` with correct session/FD attribution.

## Candidate offline protocol for a future trusted descriptor fixture
**No new M3 collection is requested or authorized by this document.** First reuse existing archived reports/logs and any verified public `hid-sony` protocol reference. If there is no usable owner Bluetooth capture, mark descriptor-specific whitelist **BLOCKED_EVIDENCE**, not PASS.

Once authorized and available, analyze *sanitized local fixtures*:
- Record provenance: original physically USB-attached DS3 identity, host adapter and session epoch privately; publish only hashes, lengths, usages and capability summaries, not addresses or link keys.
- Record raw USB descriptor separately from Bluetooth SDP/HID descriptor. Preserve transport tagging and identify transformations before comparing.
- Parse top-level HID usage pages/collections and report IDs; reject keyboard/mouse-like collections, unexpected mixed devices, malformed sizes or giant descriptors **for CablePairing path only**.
- Permit only validated gamepad-relevant usages and report types. Source-derived semantic rules needed; no hardcoded `0x01` or arbitrary fixed 49-byte Bluetooth input claim before fixture verification.
- Report filtering must be tied to immutable ACL/HID epoch and `UHID` FD; deny stale data, unexpected report ID/length and any report after revocation.
- Verify the Feature 0xF4 operational handshake occurs exactly as required by chosen kernel/native route, without duplicate injection or fabricated SET_REPORT success.
- In eventual separately authorized runtime verification, prove real DS3 button/axis changes via built-in Bluetooth to RetroArch and repeat reconnect without recabling.

## Engineering priority / disposition
**PASS**: Identify both exact pre-UHID gate functions; recover prior Sony operational-mode and USB-vs-wireless evidence; preserve User's USB-once/wireless-afterward requirement.

**BLOCKED_EVIDENCE**: exact DS3 Bluetooth descriptor/profile fixture; Sony kernel auto-initialization for the original M3 Bluetooth path.

**NO_GO**: arbitrary exact descriptor/hash whitelist from USB-only evidence; MAC-as-crypto-auth; generic keyboard HID admission; global HID security weakening; bypassing Java bond gate without reviewed session grant; declaring wirelessly functional from UHID_CREATE alone.

Maintain PR #50 as reverse-engineering archive, PR #51 separately, PR #52 draft; no device patch, HCI transmission, service restart or merge authorized.
