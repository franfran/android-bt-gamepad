#!/usr/bin/env python3
"""Offline-only Bluetooth USB HCI descriptor preflight.

Input: a deliberately sanitized, manually exported JSON descriptor sketch.
Does not enumerate USB, open device files, issue HCI, pair, or claim interfaces.
A positive match is NOT evidence of M3 USB Host availability or permission.
"""
import argparse
import json
from pathlib import Path

MAX_FILE_BYTES = 16384
# Bluetooth SIG USB HCI: wireless-controller / RF / Bluetooth interface.
BLUETOOTH_HCI_CLASS = (0xE0, 0x01, 0x01)
REQUIRED = {("interrupt", "in"), ("bulk", "in"), ("bulk", "out")}


def _byte(value):
    if type(value) is not int or not 0 <= value <= 255:
        raise ValueError("expected uint8")
    return value


def inspect_descriptor(doc):
    """Return (status, reason) with no private attributes exposed."""
    if not isinstance(doc, dict) or set(doc) != {"interfaces"}:
        return "NO_GO", "input must contain only interfaces (no private identifiers)"
    interfaces = doc["interfaces"]
    if not isinstance(interfaces, list) or len(interfaces) > 16:
        return "NO_GO", "invalid interface list"
    candidates = []
    for interface in interfaces:
        if not isinstance(interface, dict) or set(interface) != {
            "number", "alternate", "class", "subclass", "protocol", "endpoints"
        }:
            return "NO_GO", "invalid interface fields"
        try:
            number = _byte(interface["number"])
            alternate = _byte(interface["alternate"])
            triple = tuple(_byte(interface[k]) for k in ("class", "subclass", "protocol"))
        except ValueError:
            return "NO_GO", "invalid numeric descriptor fields"
        endpoints = interface["endpoints"]
        if not isinstance(endpoints, list) or len(endpoints) > 16:
            return "NO_GO", "invalid endpoint list"
        seen_addresses = set()
        endpoint_roles = set()
        for ep in endpoints:
            if not isinstance(ep, dict) or set(ep) != {"address", "type"}:
                return "NO_GO", "invalid endpoint fields"
            try:
                addr = _byte(ep["address"])
            except ValueError:
                return "NO_GO", "invalid endpoint address"
            kind = ep["type"]
            if kind not in ("interrupt", "bulk", "isochronous"):
                return "NO_GO", "unknown endpoint transfer type"
            if addr == 0 or (addr & 0x0F) == 0 or addr & 0x70 or addr in seen_addresses:
                return "NO_GO", "reserved/duplicate endpoint address"
            seen_addresses.add(addr)
            endpoint_roles.add((kind, "in" if addr & 0x80 else "out"))
        if triple == BLUETOOTH_HCI_CLASS and alternate == 0:
            candidates.append((number, endpoint_roles))
    if len(candidates) != 1:
        return "NO_GO", "expected exactly one standard Bluetooth HCI alt-0 interface"
    _, roles = candidates[0]
    if not REQUIRED.issubset(roles):
        return "NO_GO", "HCI event interrupt IN and ACL bulk IN/OUT not present"
    return "DESCRIPTOR_CANDIDATE_ONLY", (
        "standard HCI USB interface shape; physical host, permissions, firmware, "
        "exclusive claim, Classic pairing, DS3, Android input UNTESTED"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json", type=Path, help="sanitized descriptor-only JSON")
    args = parser.parse_args()
    try:
        data = args.json.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("input too large")
        document = json.loads(data)
        status, reason = inspect_descriptor(document)
    except (ValueError, OSError, UnicodeError) as exc:
        print("NO_GO:", type(exc).__name__, "(no input content printed)")
        return 2
    print(status + ": " + reason)
    return 0 if status == "DESCRIPTOR_CANDIDATE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
