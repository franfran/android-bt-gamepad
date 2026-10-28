#!/usr/bin/env python3
"""Read-only btsnoop/H4 decoder for L2CAP security chronology. Never prints PIN/key values."""
import struct, sys
EVENT = {0x17:'Link Key Request',0x16:'PIN Code Request',0x18:'Link Key Notification',0x06:'Authentication Complete',0x05:'Disconnection Complete'}
COMMAND = {0x040b:'Link Key Request Reply',0x040c:'Link Key Request Negative Reply',0x040d:'PIN Code Request Reply',0x040e:'PIN Code Request Negative Reply',0x0411:'Authentication Requested'}
L2SIG = {0x02:'Connection Request',0x03:'Connection Response',0x04:'Configuration Request',0x05:'Configuration Response'}
def main(path):
    data=open(path,'rb').read()
    if data[:8]!=b'btsnoop\0': raise SystemExit('Not a btsnoop file')
    pos=16;idx=0
    while pos+24<=len(data):
        orig,size,flags,drops,time=struct.unpack_from('>IIIIQ',data,pos);pos+=24
        if size>len(data)-pos:raise SystemExit('Truncated btsnoop')
        p=data[pos:pos+size];pos+=size;idx+=1
        if len(p)<2:continue
        if p[0]==1 and len(p)>=4:
            op=int.from_bytes(p[1:3],'little')
            if op in COMMAND: print(f'#{idx:03} HCI Command: {COMMAND[op]}')
        elif p[0]==4 and len(p)>=4:
            ev=p[1]
            if ev in EVENT:
                extra=''
                if ev==6 and len(p)>=4:extra=f' status=0x{p[3]:02x}'
                elif ev==5 and len(p)>=7:extra=f' reason=0x{p[6]:02x}'
                print(f'#{idx:03} HCI Event: {EVENT[ev]}{extra}')
        elif p[0]==2 and len(p)>=13:
            # H4 ACL: 1 packet type, 2 handle, 2 data length, 2 L2CAP payload length, 2 CID
            cid=int.from_bytes(p[7:9],'little')
            if cid!=1:continue
            sig=p[9:]
            if len(sig)<4:continue
            code=sig[0]
            if code in L2SIG:
                extra=''
                if code==2 and len(sig)>=8:
                    psm=int.from_bytes(sig[4:6],'little')
                    extra=f' PSM=0x{psm:04x}'
                print(f'#{idx:03} L2CAP signaling: {L2SIG[code]}{extra}')
    print('Total records:',idx)
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: script.py btsnoop_hci.log')
    main(sys.argv[1])
