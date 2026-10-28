#!/usr/bin/env python3
"""Read-only offline callsite inventory for the supplied M3 libbluetooth.so.
Requires: readelf and llvm-objdump. No device access and no binary modification.
"""
import bisect, re, subprocess, sys
from pathlib import Path
if len(sys.argv)!=3:
    raise SystemExit('Usage: python3 retrobox-stage3c-callgraph.py libbluetooth.so libbluetooth.debugdata.elf')
lib, debug=map(Path,sys.argv[1:])
symout=subprocess.check_output(['readelf','-Ws',str(debug)],text=True)
syms=[]
for line in symout.splitlines():
    m=re.match(r'\s*\d+:\s*([0-9a-fA-F]+)\s+(\d+)\s+FUNC\s+\w+\s+\w+\s+\S+\s+(\S+)',line)
    if m: syms.append((int(m.group(1),16)&~1,int(m.group(2)),m.group(3)))
syms.sort(); addrs=[x[0] for x in syms]
def resolve(addr):
    i=bisect.bisect_right(addrs,addr)-1
    if i<0:return 'unresolved'
    s,n,name=syms[i]
    return name if addr<s+n else 'unresolved'
for needle in ('hidh_conn_reg','hidh_l2cif_connect_ind','btm_sec_mx_access_request','btm_sec_l2cap_access_req_by_requirement'):
    matches=[x for x in syms if needle in x[2]]
    for start,size,name in matches:
        if size==0 or size>12000:continue
        print(f'\nFUNCTION {name}: 0x{start:x} size={size}')
        out=subprocess.check_output(['llvm-objdump','-d','--triple=thumbv7-linux-androideabi',f'--start-address=0x{start:x}',f'--stop-address=0x{start+size:x}',str(lib)],text=True)
        for line in out.splitlines():
            m=re.search(r'^\s*([0-9a-f]+):.*?\b(bl|blx)\s+(0x[0-9a-f]+)',line)
            if m:
                target=int(m.group(3),16)
                print(f'  0x{int(m.group(1),16):x} {m.group(2):3} 0x{target:x} -> {resolve(target)}')
