#!/usr/bin/env python3
"""Analyze sanitized RB_AUTH source-observer lines from ONE pairing attempt.

No real device I/O, no HCI operation, no PIN or MAC ingestion in reports.
Ignores unrelated line contents rather than printing them. Multiple attempts
are ambiguous because the observation patch deliberately logs no peer identity.
"""
from __future__ import annotations
import argparse
import json
import re
import sys

EVENT = re.compile(r"RB_AUTH\s+([a-z_]+)\b([^\r\n]*)")
ATTR = re.compile(r"\b([a-z_]+)=([0-9a-z_A-Z]+)\b")
STAGES = {
    "key_request", "key_notification", "pin_request", "pin_route",
    "ui_pin_reply", "java_pin_ui_dispatch", "hci_completion",
}
ROUTES = {"fixed", "preset", "ui_callback", "name_pending"}


def summarize(lines):
    events = []
    for line in lines:
        match = EVENT.search(line)
        if not match or match.group(1) not in STAGES:
            continue
        kind = match.group(1)
        props = dict(ATTR.findall(match.group(2)))
        # Only emit whitelisted, non-sensitive metadata; discard original line.
        events.append((kind, props))

    pin_requests = sum(k == "pin_request" for k, _ in events)
    hci = [d.get("status") for k, d in events if k == "hci_completion"]
    ui = [d.get("accepted") for k, d in events if k == "ui_pin_reply"]
    routes = [d.get("pin_route") for k, d in events if k == "pin_route"]
    key_known = [d.get("known") for k, d in events if k == "key_request"]
    key_generated = sum(k == "key_notification" for k, _ in events)
    forwarded_ui = any(k == "java_pin_ui_dispatch" for k, _ in events)
    ambiguous = (pin_requests > 1 or len(hci) > 1 or len(ui) > 1 or
                 len(key_known) > 1)
    status = hci[0] if len(hci) == 1 else None
    if ambiguous:
        result = "AMBIGUOUS_MULTIPLE_ATTEMPTS"
    elif not events:
        result = "NO_MATCHING_TRACE_EVENTS"
    elif not status:
        result = "NO_HCI_AUTH_COMPLETION"
    elif status == "0x00":
        result = "HCI_AUTH_REPORTED_SUCCESS"
    elif "0" in ui:
        result = "PIN_REPLY_REJECTED_WITH_HCI_FAILURE"
    elif "1" in ui:
        result = "HCI_FAILURE_AFTER_HOST_PIN_REPLY"
    elif "ui_callback" in routes or forwarded_ui or "name_pending" in routes:
        result = "PIN_HANDOFF_UNCONFIRMED"
    else:
        result = "HCI_FAILURE_PIN_PATH_UNKNOWN"

    return {
        "classification": result,
        "raw_hci_status": status,
        "event_count": len(events),
        "pin_request_events": pin_requests,
        "ui_callback_dispatched": forwarded_ui,
        "host_pin_reply_observed": bool(ui),
        "host_pin_reply_accepted": ui == ["1"],
        "key_notification_events": key_generated,
        "prior_link_key_reported_known": key_known == ["1"],
        "pin_routes_observed": sorted(set(x for x in routes if x in ROUTES)),
        "multiple_attempts_ambiguous": ambiguous,
        "source": "disabled-by-default H618 research observer, not a live finding",
        "caveat": (
            "No peer/session identifier, missing events cannot prove their "
            "underlying operation did not occur. HCI status alone cannot "
            "establish the device-side handshake root cause."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="-",
                        help="local sanitized trace file or - for stdin")
    args = parser.parse_args()
    if args.input == "-":
        report = summarize(sys.stdin)
    else:
        with open(args.input, encoding="utf-8", errors="replace") as handle:
            report = summarize(handle)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
