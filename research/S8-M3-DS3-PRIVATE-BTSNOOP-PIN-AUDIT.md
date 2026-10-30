# S8 — Historical DS3 HCI PIN/content and timing audit (read-only)

**Status:** original user-provided M3 `libbluetooth.so` is available, but a **complete btsnoop file is NOT present** among the conversation's currently mounted files. Therefore **no genuine PIN content, timing, retry behavior or local address match has been verified**. Do not infer those values from PR #41's sequence summary.

## Private offline verifier prepared

A standalone Python HCI UART btsnoop v1 parser and four synthetic regression tests were built and executed locally during this investigation. Local artifact: `retrobox_pin_audit/audit_btsnoop.py` and `retrobox_pin_audit/test_audit.py`; these files are available as conversation artifacts but **are not committed to this GitHub branch**. To keep the repo reproducible, any later code port should be reviewed and matched against these tests before promoting a release.

It reads (never modifies) the btsnoop file, supports **datalink type 1002 (HCI UART H4)**, rejects malformed packet lengths, separates authentication attempts by HCI Auth Request, and measures deltas between:
- Link Key Request → Link Key Negative Reply
- PIN Code Request → HCI PIN Reply
- PIN Reply → Authentication Complete

Optional local BD_ADDR comparison is *offline*, using `PIN == HCI-ordered address`, `PIN == reversed HCI address`, or `NEITHER`. It does **not emit** addresses, PINs, link keys or other packet payloads. If the historical capture uses a different btsnoop encapsulation, the tool must reject it rather than silently reinterpret it. It does not attempt to parse LMP directly.

## Existing evidence vs uncertainty

Original Stage 3C btsnoop **summary** indicated first DS3 incoming HID PSM 0x11 connection → Auth Request → Link Key Request/Negative → PIN Request/6-byte Reply → Authentication Complete `0x22`, followed by disconnect `0x22`. A second attempt had no corresponding PIN Reply. Without full original file, the contents/byte order, timing intervals and the reason for the second attempt's absence cannot be checked.

**Critical distinction:** HCI `0x22` is an LMP Response Timeout, **not proof of an incorrect PIN**; if a genuine payload mismatch is found, host PIN handling should be inspected, but even a match does not prove successful LMP exchange. The M3 host-side Bluetooth library already implements link key and PIN response paths (PR #41). Do not disable authentication or lower global HID PSM registration mask `0x36` based on this evidence.

## Decision and follow-up

**Evidence gate: BLOCKED — missing complete historical HCI btsnoop.** Private original capture would permit objective timing/content comparison without M3 modification. For any future run, keep Bluetooth address and PIN input private, protect shell history, and upload only the redacted JSON result if desired. No live injection, no restart, no binary replacement. C4C-3 remains **NO_GO**.

**Scope limitation:** This is not a new authentication workaround or a proof of the firmware vs DS3 failure cause; it is a trustworthy, offline evidence discriminator.
