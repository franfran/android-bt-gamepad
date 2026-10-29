#!/usr/bin/env python3
"""Offline M3 HID L2CAP callback-table verifier; no device/network access."""
import hashlib
import json
import struct
import sys
from pathlib import Path

EXPECTED_SHA256="4ce119eda2dc211cb38085e8fde3d7ee2fbaaa243df9b20e21636e3c4962bd85"
TABLE_VMA=0x5e50d0
EXPECTED=(0x27ee29,0x27f0f9,0x27f2ad,0x27f331,0x27f6a5,0x27f8c5,
          0x27fa21,0,0x27fa99,0,0,0)
def analyze(data):
    if hashlib.sha256(data).hexdigest()!=EXPECTED_SHA256:
        raise ValueError("M3_ELF_SHA256_MISMATCH")
    if data[:4]!=b"\x7fELF" or data[4]!=1 or data[5]!=1 or struct.unpack_from("<H",data,18)[0]!=40:
        raise ValueError("NOT_ARM32_LITTLE_ENDIAN_ELF")
    phoff=struct.unpack_from("<I",data,28)[0]
    ents,n=struct.unpack_from("<HH",data,42)
    if ents<32 or n>64 or phoff+n*ents>len(data):
        raise ValueError("INVALID_ELF_PROGRAM_HEADERS")
    segments=[]
    for i in range(n):
        p_type,p_off,vaddr,_paddr,filesz,_memsz,_flags,_align=struct.unpack_from("<IIIIIIII",data,phoff+i*ents)
        if p_type==1 and p_off+filesz<=len(data):
            segments.append((vaddr,vaddr+filesz,p_off))
    def read(vma,count):
        matches=[(a,b,off) for a,b,off in segments if a<=vma and vma+count<=b]
        if len(matches)!=1:raise ValueError("AMBIGUOUS_OR_UNMAPPED_VMA")
        a,b,off=matches[0]
        return data[off+vma-a:off+vma-a+count]
    # Original Thumb disassembly: literal loads 0x27e820, 0x27e828;
    # add r1,pc at 0x27e75c and 0x27e7aa, respectively.
    literal_a=struct.unpack("<I",read(0x27e820,4))[0]
    literal_b=struct.unpack("<I",read(0x27e828,4))[0]
    table_a=(0x27e760+literal_a)&0xffffffff
    table_b=(0x27e7ae+literal_b)&0xffffffff
    if table_a!=TABLE_VMA or table_b!=TABLE_VMA:
        raise ValueError("CALLBACK_POINTER_NOT_SHARED")
    entries=struct.unpack("<"+"I"*len(EXPECTED),read(TABLE_VMA,4*len(EXPECTED)))
    if entries!=EXPECTED:raise ValueError("CALLBACK_ENTRIES_CHANGED")
    return {"stage":"S8","source":"EXACT_SHA256_VERIFIED_ORIGINAL_M3_ARM32_ELF",
            "callback_table_vma":hex(TABLE_VMA),
            "l2cap_registration_psms":["0x0011","0x0013"],
            "same_callback_table_both_psms":True,
            "callback_entries":[{"offset":hex(i*4),"thumb_symbol_vma":hex(v) if v else "NULL"}
                                for i,v in enumerate(entries)],
            "first_callback":"hidh_l2cif_connect_ind",
            "hid_callback_registration":"STATIC_BINARY_VERIFIED",
            "callback_execution_at_runtime":"UNVERIFIED",
            "security_btm_dispatch":"UNVERIFIED",
            "bluetooth_service_modification":False,"injection_authorized":False,
            "decision":"NO_GO"}
def main():
    if len(sys.argv)!=2:
        print("Usage: verify_callback_table.py LOCAL_ORIGINAL_M3_libbluetooth.so",file=sys.stderr)
        return 2
    try:
        path=Path(sys.argv[1])
        if not path.is_file() or path.stat().st_size>16*1024*1024:
            raise ValueError("INVALID_LOCAL_ELF")
        obj=analyze(path.read_bytes())
    except (OSError,ValueError,struct.error) as e:
        msg=str(e) if isinstance(e,ValueError) else "READ_FAILED"
        print(json.dumps({"error":msg,"decision":"NO_GO","injection_authorized":False}),file=sys.stderr)
        return 2
    print(json.dumps(obj,indent=2,sort_keys=True))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
