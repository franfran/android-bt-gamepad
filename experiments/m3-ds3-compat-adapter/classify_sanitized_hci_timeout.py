#!/usr/bin/env python3
"""Host-only classification of sanitized, single-ACL HCI event timelines.

No HCI or device access. Accept only a strict allowlist of relative elapsed
times, HCI event kinds and numeric status codes. Never accept raw addresses,
PINs, LinkKeys, timestamps, packet payloads or logcat strings. No proof of
remote PIN acceptance or a viable DS3 plugin is inferred.
"""
import argparse
import json
from pathlib import Path

KINDS = frozenset({
    "connection_complete", "authentication_requested", "link_key_request",
    "link_key_negative_reply", "pin_code_request", "pin_code_reply",
    "pin_code_negative_reply", "authentication_complete", "disconnection_complete",
})
STATUSES = {"connection_complete", "authentication_complete", "disconnection_complete"}
MAX_BYTES = 12000


def classify(session):
    if not isinstance(session, dict) or set(session) != {"capture_complete", "events"}:
        raise ValueError("input must contain only capture_complete and events")
    if type(session["capture_complete"]) is not bool:
        raise ValueError("capture_complete must be a boolean")
    events = session["events"]
    if not isinstance(events, list) or not 1 <= len(events) <= 32:
        raise ValueError("event list out of bounds")

    seq = []
    last_ms = -1
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("invalid event")
        kind = event.get("kind")
        if kind not in KINDS:
            raise ValueError("unrecognized HCI event")
        expected = {"kind", "elapsed_ms"} | ({"status"} if kind in STATUSES else set())
        if set(event) != expected:
            raise ValueError("unexpected field or missing required field")
        ms = event["elapsed_ms"]
        if type(ms) is not int or not 0 <= ms <= 120000 or ms < last_ms:
            raise ValueError("invalid relative event time or ordering")
        last_ms = ms
        if kind in STATUSES:
            status = event["status"]
            if type(status) is not int or not 0 <= status <= 255:
                raise ValueError("status must be 8-bit integer")
        seq.append(event)

    pins = [x for x in seq if x["kind"] == "pin_code_request"]
    completions = [x for x in seq if x["kind"] == "authentication_complete"]
    replies = [x for x in seq if x["kind"] in ("pin_code_reply", "pin_code_negative_reply")]
    if len(pins) != 1 or len(completions) != 1 or len(replies) > 1:
        classification = "AMBIGUOUS_HCI_WINDOW"
    elif completions[0]["elapsed_ms"] <= pins[0]["elapsed_ms"]:
        classification = "AMBIGUOUS_HCI_WINDOW"
    elif not session["capture_complete"]:
        classification = "INCOMPLETE_CAPTURE_NO_ABSENCE_CLAIM"
    elif completions[0]["status"] == 0x22 and not replies:
        classification = "NO_PIN_HCI_REPLY_OBSERVED_THEN_LMP_TIMEOUT"
    elif completions[0]["status"] == 0x22:
        classification = "HCI_PIN_REPLY_OBSERVED_THEN_LMP_TIMEOUT"
    elif completions[0]["status"] == 0x05:
        classification = "AUTHENTICATION_FAILURE_STATUS_0X05"
    elif completions[0]["status"] == 0:
        classification = "HCI_AUTHENTICATION_REPORTED_SUCCESS"
    else:
        classification = "OTHER_HCI_AUTH_COMPLETION"

    tpin = pins[0]["elapsed_ms"] if len(pins) == 1 else None
    tcomplete = completions[0]["elapsed_ms"] if len(completions) == 1 else None
    result = {
        "classification": classification,
        "hci_auth_status": f"0x{completions[0]['status']:02X}" if len(completions) == 1 else None,
        "pin_to_auth_complete_ms": tcomplete - tpin if tpin is not None and tcomplete is not None and tcomplete > tpin else None,
        "pin_reply_hci_command_observed": any(x["kind"] == "pin_code_reply" for x in replies),
        "pin_negative_reply_hci_command_observed": any(x["kind"] == "pin_code_negative_reply" for x in replies),
        "input_hci_window_marked_complete": session["capture_complete"],
        "caveat": "HCI command observation is not peer acceptance; 0x22 is LMP Response Timeout, not 0x05 wrong PIN evidence; no causal proof or DS3 plugin proof.",
    }
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("sanitized_json", type=Path)
    a = p.parse_args()
    try:
        raw = a.sanitized_json.read_bytes()
        if len(raw) > MAX_BYTES:
            raise ValueError("input too large")
        report = classify(json.loads(raw))
    except (ValueError, OSError, TypeError, UnicodeError) as error:
        print("NO_GO: sanitized HCI input refused (" + type(error).__name__ + ")")
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
