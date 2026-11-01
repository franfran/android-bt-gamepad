#!/usr/bin/env python3
"""Fail-closed source-byte checks of owner M3 2024 native dispatcher.

This does NOT prove that there is no alternate UHID reply writer.
All addresses are ELF VMAs and must not be used as live patch locations.
"""
import hashlib
import pathlib
import sys

EXPECTED_SHA = "4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85"
TEXT_VMA_MINUS_FILE_OFFSET = 0x1000

# Original Thumb bytes for dispatcher branch and their direct BL targets.
# The first case invokes the logging-only SET_REPORT callback; the second
# routes GET_REPORT through a distinct helper.
INSTRUCTIONS = {
    0x15CA88: bytes.fromhex("05 28"),            # cmp r0,#5
    0x15CA94: bytes.fromhex("4a f0 aa fa"),      # bl 0x1a6fec
    0x15CB04: bytes.fromhex("04 28"),            # cmp r0,#4
    0x15CB14: bytes.fromhex("4a f0 80 fa"),      # bl 0x1a7018
    0x1A6FF6: bytes.fromhex("08 bf 70 47"),      # it eq; bxeq lr
    0x1A7006: bytes.fromhex("19 f1 df bb"),      # tail call logger
}

def inspect(data):
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA:
        raise ValueError("not the original 2024 M3 libbluetooth.so")
    for addr, expected in INSTRUCTIONS.items():
        offset = addr - TEXT_VMA_MINUS_FILE_OFFSET
        if data[offset:offset+len(expected)] != expected:
            raise AssertionError(f"instruction mismatch at ELF VMA 0x{addr:x}")
    if data.count(b"UHID_SET_REPORT_REPLY not supported") != 1:
        raise AssertionError("unexpected SET_REPORT unsupported marker count")
    return {
        "sha256": digest,
        "set_event5": "compiled call to log-only callback at VMA 0x1a6fec",
        "get_event4": "separate helper at VMA 0x1a7018",
        "reply_writer_exhaustively_excluded": False,
        "runtime_reachability_verified": False,
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python verify_m3_report_dispatch.py /private/libbluetooth.so")
    print(inspect(pathlib.Path(sys.argv[1]).read_bytes()))
