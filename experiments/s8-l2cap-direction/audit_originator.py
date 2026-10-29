#!/usr/bin/env python3
"""Read-only Thumb disassembly audit of originator flags at M3 security callsites.

Use with disassembly from the SHA-verified owner's original ELF; no device access.
The state/event branch taken at runtime is NOT established by this audit.
"""
import argparse
import json
import re
import sys
from pathlib import Path

EXPECTED={
    0x286ea8:(0x286ea2,0),0x288b20:(0x288b1e,1),
    0x2897b4:(0x2897ae,0),0x289808:(0x289802,1),
    0x2898aa:(0x2898a8,1),
}
LINE=re.compile(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f]{4}\s+)+([a-z][a-z0-9.]*)\s+([^@<]*)(?:\s+.*)?$",re.I)

def audit(disassembly):
    ins={}
    for s in disassembly.splitlines():
        m=LINE.match(s)
        if m:
            addr=int(m.group(1),16)
            if addr in ins:raise ValueError("DUPLICATE_INSTRUCTION")
            ins[addr]=(m.group(2),m.group(3).strip())
    results=[]
    for call,(movaddr,direction) in EXPECTED.items():
        opname,opargs=ins.get(call,("", ""))
        if opname!="bl" or not re.match(r"0x258e68\b",opargs):
            raise ValueError("MISSING_OR_CHANGED_SECURITY_CALLSITE")
        opname,opargs=ins.get(movaddr,("", ""))
        if opname!="movs" or not re.fullmatch(r"r2,\s*#0x%x"%direction,opargs):
            raise ValueError("UNVERIFIED_ORIGINATOR_ARGUMENT")
        # The flag-setting instruction is adjacent to the BL, at most 6 bytes.
        # Future control-flow audit still needed for state selection.
        results.append({"site":hex(call),"originator":bool(direction),
                        "direction_instruction":hex(movaddr)})
    return {"mode":"OFFLINE_CSM_SECURITY_DIRECTION_AUDIT","stage":"S8",
            "verified_direction_callsites":results,
            "incoming_direction_candidates":[hex(a) for a,(i,d) in EXPECTED.items() if not d],
            "outgoing_direction_callsites":[hex(a) for a,(i,d) in EXPECTED.items() if d],
            "runtime_event_selection":"UNVERIFIED",
            "exact_ds3_hid_psm_path":"UNVERIFIED",
            "injection_authorized":False,"decision":"NO_GO"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("thumb_disassembly",help="Local, offline original M3 disassembly text")
    args=p.parse_args()
    try:
        f=Path(args.thumb_disassembly)
        if f.stat().st_size>1024*1024:
            raise ValueError("OVERSIZE_INPUT")
        result=audit(f.read_text(encoding="utf8"))
    except (OSError,UnicodeError,ValueError):
        print(json.dumps({"error":"STATIC_DIRECTION_EVIDENCE_INVALID",
                          "decision":"NO_GO","injection_authorized":False}),file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0
if __name__=="__main__":
    sys.exit(main())
