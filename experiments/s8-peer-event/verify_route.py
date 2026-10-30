#!/usr/bin/env python3
"""Fail-closed verification of exact M3 CSM state/event security route; offline only."""
import hashlib,json,struct,sys
from pathlib import Path
SHA="4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85"
CHECKS={
 0x2861c6:"56f8040f", # ldr r0,[r6,#4]!
 0x2861ca:"0828", # cmp r0,#8
 0x2861ce:"dfe810f0", # state TBH
 0x286242:"00f05c85", # beq event dispatch at 0x286cfe
 0x286cfe:"b8f12d0f", # cmp r8,#45
 0x286d0a:"dfe818f0", # event TBH
 0x28867e:"90f8c910", # ldrb r1,[r0,#0xc9]
 0x288682:"0229", # cmp r1,#2
 0x288684:"41f07580", # bne Classic branch
 0x2897ae:"0022", # incoming r2=false
 0x2897b4:"cff758fb", # BL btm_sec_l2cap_access_req
 0x2897c4:"07f0e8fb", # BL l2cu_send_peer_connect_rsp
}
def verify(data,expected_sha=SHA):
    if hashlib.sha256(data).hexdigest()!=expected_sha:raise ValueError("ELF_SHA_MISMATCH")
    if data[:6]!=b"\x7fELF\x01\x01" or len(data)<52 or struct.unpack_from("<H",data,18)[0]!=40:
        raise ValueError("NOT_ELF32_ARM")
    phoff=struct.unpack_from("<I",data,28)[0];ents,n=struct.unpack_from("<HH",data,42)
    if ents<32 or n>128 or phoff+n*ents>len(data):raise ValueError("BAD_PROGRAM_HEADERS")
    segs=[]
    for i in range(n):
        typ,off,vma,_,sz,_,_,_=struct.unpack_from("<IIIIIIII",data,phoff+i*ents)
        if typ==1 and off+sz<=len(data):segs.append((vma,vma+sz,off))
    def read(addr,sz):
        positions=[off+addr-a for a,b,off in segs if a<=addr and addr+sz<=b]
        if len(positions)!=1:raise ValueError("AMBIGUOUS_VMA")
        pos=positions[0];return data[pos:pos+sz]
    for addr,hx in CHECKS.items():
        if read(addr,len(hx)//2)!=bytes.fromhex(hx):raise ValueError("MISMATCH_AT_%x"%addr)
    state=0x2861d2+2*struct.unpack("<H",read(0x2861d2,2))[0]
    event=0x286d0e+2*struct.unpack("<H",read(0x286d0e+20,2))[0]
    if (state,event)!=(0x2861e4,0x288670):raise ValueError("DISPATCH_MISMATCH")
    return {"state_index":0,"state_target":hex(state),
            "event_index":10,"event_target":hex(event),
            "aosp_event_name":"L2CEVT_L2CAP_CONNECT_REQ",
            "classic_security_call":"0x2897b4",
            "conditional_state0_dispatch":True,
            "static_branch_verified":True,
            "actual_ds3_runtime_path":"UNVERIFIED",
            "hci_0x22_root_cause":"UNVERIFIED",
            "decision":"NO_GO","injection_authorized":False}
if __name__=="__main__":
    try:
        if len(sys.argv)!=2:raise ValueError("USAGE")
        p=Path(sys.argv[1])
        if not 0<p.stat().st_size<=16*1024*1024:raise ValueError("SIZE")
        print(json.dumps(verify(p.read_bytes()),indent=2,sort_keys=True))
    except (ValueError,OSError,struct.error) as e:
        print(json.dumps({"error":str(e) if isinstance(e,ValueError) else "READ_FAILURE",
                          "decision":"NO_GO","injection_authorized":False}),file=sys.stderr)
        sys.exit(2)
