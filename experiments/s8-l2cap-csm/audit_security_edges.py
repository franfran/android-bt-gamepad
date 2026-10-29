#!/usr/bin/env python3
"""Fail-closed static evidence assertions on real ELF disassembly TEXT only."""
import argparse
import json
import re
import sys
from pathlib import Path

EXPECTED = {
    0x286ea8: 0x258e68,
    0x288b20: 0x258e68,
    0x2897b4: 0x258e68,
    0x289808: 0x258e68,
    0x2898aa: 0x258e68,
    0x258ffe: 0x258734,
    0x258b5a: 0x257c04,
}
CALL = re.compile(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f]{4}\s+)+bl\s+(0x[0-9a-f]+)\b", re.I)

def audit(disassembly):
    found={}
    for line in disassembly.splitlines():
        match=CALL.match(line)
        if match:
            site,target=int(match.group(1),16),int(match.group(2),16)
            if site in EXPECTED:
                if site in found: raise ValueError("DUPLICATE_CALLSITE")
                found[site]=target
    if found!=EXPECTED:
        raise ValueError("EXPECTED_DIRECT_EDGE_MISSING_OR_CHANGED")
    return {"stage":"S8","mode":"OFFLINE_CSM_BTM_DIRECT_EDGE_AUDIT",
            "verified_direct_edges":len(EXPECTED),
            "l2cap_csm_to_btm_callsite_count":5,
            "incoming_ds3_state_selection":"UNVERIFIED",
            "runtime_authentication_trigger":"UNVERIFIED",
            "decision":"NO_GO","injection_authorized":False}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("offline_thumb_disassembly")
    args=parser.parse_args(argv)
    try:
        path=Path(args.offline_thumb_disassembly)
        if path.stat().st_size>1024*1024:
            raise ValueError("OVERSIZE")
        result=audit(path.read_text(encoding="utf8"))
    except (OSError,ValueError,UnicodeError):
        print(json.dumps({"error":"INVALID_OR_INCOMPLETE_STATIC_EVIDENCE",
                          "decision":"NO_GO","injection_authorized":False}),file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
