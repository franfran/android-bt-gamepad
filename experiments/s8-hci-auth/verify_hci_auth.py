#!/usr/bin/env python3
"""Offline fail-closed verifier for authenticated M3 Bluetooth native HCI evidence."""
import hashlib,json,struct,sys
from pathlib import Path
SHA='4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85'
# Raw LITTLE-ENDIAN Thumb instruction bytes recovered from the original M3 ELF.
INSTRUCTIONS={
  0x2580bc:'84f82951', # strb.w r5,[r4,#0x129] security state
  0x2580c0:'24f06afc', # BL btsnd_hcic_auth_request at 0x27c998
  0x27c99c:'4ff42570', # mov.w r0,#0x294 packet allocation
  0x27c9ae:'40f21140', # movw r0,#0x0411 HCI Authentication Requested
  0x27c9b2:'0881', # strh r0,[r1,#8] opcode in packet
  0x25b5e6:'8df8af10', # btm_sec_auth_complete copies status r1 to local stack
}
def audit(b,expected=SHA):
    if hashlib.sha256(b).hexdigest()!=expected:raise ValueError('SHA_MISMATCH')
    if len(b)<52 or b[:6]!=b'\x7fELF\x01\x01' or struct.unpack_from('<H',b,18)[0]!=40:
        raise ValueError('NOT_ELF32_ARM')
    off=struct.unpack_from('<I',b,28)[0]
    ents,n=struct.unpack_from('<HH',b,42)
    if ents<32 or n>128 or off+ents*n>len(b):raise ValueError('INVALID_HEADER')
    def fetch(addr,size):
        hits=[]
        for i in range(n):
            typ,base,vma,_,filesz,_,_,_=struct.unpack_from('<IIIIIIII',b,off+ents*i)
            if typ==1 and vma<=addr and addr+size<=vma+filesz and base+filesz<=len(b):
                hits.append(b[base+addr-vma:base+addr-vma+size])
        if len(hits)!=1:raise ValueError('VMA_NOT_UNIQUE')
        return hits[0]
    for addr,hx in INSTRUCTIONS.items():
        if fetch(addr,len(hx)//2)!=bytes.fromhex(hx):
            raise ValueError('INSTRUCTION_MISMATCH_0x%x'%addr)
    return {'exact_m3_sha256':SHA,
            'native_auth_function':'btm_sec_execute_procedure @ 0x257c04',
            'native_auth_callsite':'0x2580c0',
            'hci_builder':'btsnd_hcic_auth_request @ 0x27c998',
            'hci_opcode':'0x0411',
            'completion_handler':'btm_sec_auth_complete @ 0x25b5c4',
            'completion_status_argument':'r1 (stored to stack at 0x25b5e6)',
            'hci_0x22_lmp_timeout_cause':'UNVERIFIED',
            'runtime_ds3_branch_predicate':'UNVERIFIED',
            'bluetooth_operation':'NONE','injection_authorized':False,'decision':'NO_GO'}
def main():
    try:
        if len(sys.argv)!=2:raise ValueError('USAGE')
        p=Path(sys.argv[1])
        if not 0<p.stat().st_size<16*1024*1024:raise ValueError('SIZE')
        print(json.dumps(audit(p.read_bytes()),indent=2))
    except (OSError,ValueError,struct.error) as e:
        print(json.dumps({'error':str(e) if isinstance(e,ValueError) else 'INVALID_INPUT','decision':'NO_GO'}),file=sys.stderr)
        return 2
    return 0
if __name__=='__main__':sys.exit(main())
