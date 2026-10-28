#!/usr/bin/env python3
"""Minimal read-only btsnoop HCI security event auditor. Does not print PIN/link-key material."""
import sys, struct

EVENT = {0x17:'Link Key Request', 0x16:'PIN Code Request', 0x18:'Link Key Notification',
         0x06:'Authentication Complete', 0x05:'Disconnection Complete'}
COMMAND = {0x040b:'Link Key Request Reply', 0x040c:'Link Key Request Negative Reply',
           0x040d:'PIN Code Request Reply', 0x040e:'PIN Code Request Negative Reply'}

def main(path):
    with open(path, 'rb') as fd: data=fd.read()
    if len(data)<16 or data[:8]!=b'btsnoop\x00': raise SystemExit('Not a btsnoop file')
    pos=16; count=0
    while pos+24<=len(data):
        original,included,flags,drops,t=struct.unpack_from('>IIIIQ',data,pos); pos+=24
        if included>len(data)-pos:raise SystemExit('Truncated record')
        p=data[pos:pos+included];pos+=included;count+=1
        if len(p)<2:continue
        if p[0]==4 and p[1] in EVENT:
            code=p[1];extra=''
            if code==6 and len(p)>=4:extra=f' status=0x{p[3]:02x}'
            if code==5 and len(p)>=7:extra=f' reason=0x{p[6]:02x}'
            print(f'#{count:03} EVENT   {EVENT[code]}{extra}')
        elif p[0]==1 and len(p)>=4:
            op=int.from_bytes(p[1:3],'little')
            if op in COMMAND:print(f'#{count:03} COMMAND {COMMAND[op]}')
    print('Total HCI records:',count)
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python3 retrobox-stage3c-hci-audit.py btsnoop_hci.log')
    main(sys.argv[1])
