#!/usr/bin/env python3
"""Fail-closed offline audit of M3 peer-connection pending security branch."""
import re
import sys
from pathlib import Path
EXPECTED={
 0x289798:("movs","r3, #0x2"),
 0x2897a4:("str.w","r3, [r10, #0x4]"),
 0x2897a8:("ldrh","r1, [r1, #0x2]"),
 0x2897ae:("movs","r2, #0x0"),
 0x2897b4:("bl","0x258e68"),
 0x2897b8:("cmp","r0, #0x1"),
 0x2897bc:("bne","0x2898b0"),
 0x2897c0:("movs","r1, #0x1"),
 0x2897c2:("movs","r2, #0x0"),
 0x2897c4:("bl","0x290f98"),
}
PATTERN=re.compile(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f]{4}\s+)+([a-z.]+)\s+([^@<]*).*")
def audit(source):
    got={}
    for line in source.splitlines():
        m=PATTERN.match(line)
        if m and int(m.group(1),16) in EXPECTED:
            addr=int(m.group(1),16)
            if addr in got:raise ValueError("duplicate instruction")
            got[addr]=(m.group(2),m.group(3).strip())
    if got!=EXPECTED:raise ValueError("missing/changed instruction")
    return {"verified":len(got),"peer_connect_response":True,"event_dispatch_predecessor":"UNVERIFIED",
            "ds3_runtime_path":"UNVERIFIED","decision":"NO_GO"}
if __name__=="__main__":
    try:
        if len(sys.argv)!=2:raise ValueError("usage")
        path=Path(sys.argv[1])
        if path.stat().st_size>1024*1024:raise ValueError("oversize")
        import json
        print(json.dumps(audit(path.read_text())))
    except (OSError,ValueError):
        print('{"error":"INVALID_STATIC_EVIDENCE","decision":"NO_GO"}',file=sys.stderr)
        sys.exit(2)
