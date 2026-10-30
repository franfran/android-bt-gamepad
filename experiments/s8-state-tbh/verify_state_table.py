#!/usr/bin/env python3
"""Verify true CSM state TBH targets in exact original M3 ELF, offline only."""
import hashlib,json,struct,sys
from pathlib import Path
EXPECTED_SHA="4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85"
TBH_ADDR=0x2861ce
TABLE_ADDR=0x2861d2
EXPECTED=[0x2861e4,0x28627c,0x28630c,0x286372,0x2863f4,0x2864e0,
          0x286560,0x2865d0,0x286636]

def verify(data,sha=EXPECTED_SHA):
    if hashlib.sha256(data).hexdigest()!=sha:
        raise ValueError("SHA256_NOT_EXACT_M3_ELF")
    if len(data)<52 or data[:6]!=b"\x7fELF\x01\x01" or struct.unpack_from("<H",data,18)[0]!=40:
        raise ValueError("NOT_ARM32_ELF")
    phoff=struct.unpack_from("<I",data,28)[0]
    ents,num=struct.unpack_from("<HH",data,42)
    if ents<32 or num>64 or phoff+ents*num>len(data):raise ValueError("INVALID_HEADERS")
    def read(vma,n):
        hits=[]
        for i in range(num):
            kind,offset,start,_,filesz,*_=struct.unpack_from("<IIIIIIII",data,phoff+i*ents)
            if kind==1 and start<=vma and vma+n<=start+filesz and offset+filesz<=len(data):
                hits.append(data[offset+vma-start:offset+vma-start+n])
        if len(hits)!=1:raise ValueError("NOT_UNIQUELY_MAPPED")
        return hits[0]
    if read(TBH_ADDR,4)!=bytes.fromhex("dfe810f0"):
        raise ValueError("TBH_OPCODE_MISMATCH")
    offsets=struct.unpack("<9H",read(TABLE_ADDR,18))
    targets=[TABLE_ADDR+2*i for i in offsets]
    if targets!=EXPECTED:raise ValueError("STATE_TARGETS_MISMATCH")
    return {"state_selector":"ldr r0,[r10,#4]; cmp r0,#8; tbh [pc,r0,lsl #1]",
            "tbh_vma":hex(TBH_ADDR),
            "states":[{"index":i,"destination":hex(t)} for i,t in enumerate(targets)],
            "state_table":"STATIC_BINARY_VERIFIED",
            "event_to_state_mapping":"UNVERIFIED",
            "incoming_ds3_execution":"UNVERIFIED",
            "decision":"NO_GO","injection_authorized":False}

def main():
    try:
        if len(sys.argv)!=2:raise ValueError("USAGE")
        path=Path(sys.argv[1])
        if not 0<path.stat().st_size<=16*1024*1024:raise ValueError("SIZE")
        print(json.dumps(verify(path.read_bytes()),indent=2))
    except (OSError,ValueError,struct.error) as e:
        print(json.dumps({"error":str(e) if isinstance(e,ValueError) else "READ_ERROR","decision":"NO_GO"}),file=sys.stderr)
        return 2
    return 0
if __name__=="__main__":raise SystemExit(main())
