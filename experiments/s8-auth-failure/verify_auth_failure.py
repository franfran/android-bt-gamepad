#!/usr/bin/env python3
"""Read-only exact-original M3 ELF evidence checker for auth guards and 0x22."""
import hashlib,json,struct,sys
from pathlib import Path
SHA="4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85"
# Individual Thumb machine instruction bytes, NEVER runtime patch offsets.
CHECKS={
 0x258032:"94f82a01", # auth prerequisite state
 0x258038:"45d1", # nonzero diverts
 0x258042:"208a", # link handle
 0x25804a:"3cd0", # invalid handle diverts
 0x2580a2:"e08d", # security flag field
 0x2580b4:"00f0ec80", # conditional alternate
 0x2580bc:"84f82951", # state=1
 0x2580c0:"f024fc6a", # call HCI auth sender
 0x25b5e6:"8df8af10", # save HCI status
 0x25b78a:"2a2e", # status 0x2a
 0x25b78e:"232e", # status 0x23
 0x25b790:"0cd1", # neither => common path
 0x25b7ba:"00f0fd01", # clear security flag
 0x25b836:"9af82901", # authentication state
 0x25b844:"8af82951", # reset authentication state
 0x25b848:"0028", # compare status with success
 0x25b84c:"0c28", # special status 0x0c
 0x25b84e:"4cd1", # non-0x0c error
 0x25b934:"b847", # guarded callback BLX
}
def audit(raw,sha=SHA):
    if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError("SHA_MISMATCH")
    if len(raw)<52 or raw[:6]!=b"\x7fELF\x01\x01" or struct.unpack_from("<H",raw,18)[0]!=40:
        raise ValueError("INVALID_ELF32_ARM")
    phoff=struct.unpack_from("<I",raw,28)[0]
    ents,n=struct.unpack_from("<HH",raw,42)
    if ents<32 or n>64 or phoff+n*ents>len(raw):raise ValueError("INVALID_PHDR")
    for addr,hexbytes in CHECKS.items():
        size=len(hexbytes)//2
        mappings=[]
        for i in range(n):
            typ,off,vma,_,filesz,_,_,_=struct.unpack_from("<IIIIIIII",raw,phoff+i*ents)
            if typ==1 and vma<=addr and addr+size<=vma+filesz and off+filesz<=len(raw):
                mappings.append(raw[off+addr-vma:off+addr-vma+size])
        if len(mappings)!=1 or mappings[0]!=bytes.fromhex(hexbytes):
            raise ValueError("ORIGINAL_INSTRUCTION_MISMATCH_0x%x"%addr)
    return {"verified_thumb_instructions":len(CHECKS),"auth_request_conditional":True,
            "status_0x22_is_nonzero_failure":True,
            "auth_state_reset_site":"0x25b844",
            "guarded_indirect_callback":"0x25b934",
            "root_cause_of_lmp_timeout":"UNVERIFIED",
            "actual_ds3_callback":"UNVERIFIED","injection_authorized":False,"decision":"NO_GO"}
if __name__=="__main__":
    try:
        if len(sys.argv)!=2:raise ValueError("USAGE")
        p=Path(sys.argv[1])
        if not 0<p.stat().st_size<16*1024*1024:raise ValueError("ELF_SIZE")
        print(json.dumps(audit(p.read_bytes()),indent=2,sort_keys=True))
    except (OSError,ValueError,struct.error) as e:
        print(json.dumps({"error":str(e) if isinstance(e,ValueError) else "READ_ERROR","decision":"NO_GO"}),file=sys.stderr)
        sys.exit(2)
