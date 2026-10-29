#!/usr/bin/env python3
"""Offline assert only explicitly identified ARM32 symbol/callsite relationships.

This is an evidence contract, not a disassembler or patch tool.
"""
import argparse
import json
import re
import sys
from pathlib import Path

FUNCTIONS = {
    "_Z13hidh_conn_regv": (0x27e748, 232),
    "_ZL22hidh_l2cif_connect_indRK10RawAddresstth": (0x27ee28, 720),
    "_Z25btm_sec_mx_access_requestRK10RawAddressbtPFvPS0_hPvhES3_": (0x2590a8, 1904),
    "_Z39btm_sec_l2cap_access_req_by_requirementRK10RawAddresstbPFvPS0_hPvhES3_": (0x258734, 1564),
}
EXPECTED_EDGES = {
    "_Z13hidh_conn_regv": [(0x27e79c, 0x281368), (0x27e7b2, 0x281368)],
    "_Z25btm_sec_mx_access_requestRK10RawAddressbtPFvPS0_hPvhES3_": [
        (0x2590d2, 0x2eff7e), (0x2590e2, 0x2cf5c2), (0x2592dc, 0x257c04)],
    "_Z39btm_sec_l2cap_access_req_by_requirementRK10RawAddresstbPFvPS0_hPvhES3_": [
        (0x258b5a, 0x257c04)],
}
CALL = re.compile(r"^\s*(0x[0-9a-f]+)\s+(bl|blx)\s+(0x[0-9a-f]+)\s+->\s+(\S+)")
FUNC = re.compile(r"^FUNCTION (\S+): (0x[0-9a-f]+) size=(\d+)$")


def audit(text):
    blocks = {}
    cur = None
    for line in text.splitlines():
        m=FUNC.fullmatch(line.strip())
        if m:
            name,address,size=m.group(1),int(m.group(2),16),int(m.group(3))
            if name in blocks:
                raise ValueError("duplicate function")
            blocks[name]={"address":address,"size":size,"edges":set(),"unresolved":0}
            cur=name
            continue
        m=CALL.match(line)
        if m and cur:
            site=int(m.group(1),16)
            target=int(m.group(3),16)
            if m.group(4)=="unresolved":
                blocks[cur]["unresolved"]+=1
            else:
                blocks[cur]["edges"].add((site,target))
    verified=[]
    for name,(addr,size) in FUNCTIONS.items():
        b=blocks.get(name)
        if not b or b["address"]!=addr or b["size"]!=size:
            raise ValueError("missing or mismatched recovered function")
        edges=EXPECTED_EDGES.get(name,[])
        for edge in edges:
            if edge not in b["edges"]:
                raise ValueError("missing explicit call edge")
        verified.append({"symbol":name,"function_start":hex(addr),
                         "required_edges_verified":len(edges),
                         "indirect_or_unresolved_calls":b["unresolved"]})
    return {"mode":"OFFLINE_BT_SECURITY_CALLGRAPH_CONTRACT","stage":"S8",
            "checked_functions":verified,
            "verified_edges":sum(map(len,EXPECTED_EDGES.values())),
            "hid_to_l2cap_security_dispatch":"UNVERIFIED",
            "hid_callback_to_btm_auth":"UNVERIFIED",
            "runtime_gd_or_legacy_branch":"UNVERIFIED",
            "security_exception_safe":"UNVERIFIED",
            "cause_of_hci_0x22":"UNVERIFIED",
            "decision":"NO_GO","injection_authorized":False}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("callgraph",help="offline recovered callgraph text (no target execution)")
    args=ap.parse_args()
    try:
        path=Path(args.callgraph)
        if path.stat().st_size>2*1024*1024:
            raise ValueError("oversized input")
        result=audit(path.read_text(encoding="utf-8"))
    except (OSError,ValueError,UnicodeError):
        print(json.dumps({"mode":"OFFLINE_BT_SECURITY_CALLGRAPH_CONTRACT",
                          "error":"missing or inconsistent static evidence",
                          "decision":"NO_GO","injection_authorized":False}),file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
