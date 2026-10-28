#!/usr/bin/env python3
"""Read-only RetroBox D2b-2d-B ARM32 ELF/mapping inspector; NO injection."""
import argparse, pathlib, re, struct, subprocess, sys

PATH = '/apex/com.android.runtime/lib/bionic/libdl.so'
MAP_RE = re.compile(r'^([0-9a-f]+)-([0-9a-f]+)\s+([rwxps-]{4})\s+([0-9a-f]+)\s+\S+\s+\d+\s+(.*)$')

def adb(device,*args):
    return subprocess.check_output(['adb','-s',device,*args],stderr=subprocess.PIPE).decode('utf-8','replace')

def parse_elf(blob):
    if blob[:5]!=b'\x7fELF\x01' or blob[5]!=1 or blob[18:20]!=b'\x28\x00':
        raise ValueError('Expected little-endian ELF32 ARM file')
    (_,_,_,_,_,phoff,shoff,_,_,phentsize,phnum,shentsize,shnum,_)=struct.unpack_from('<16sHHIIIIIHHHHHH',blob,0)
    ph=[]
    for i in range(phnum):
        offset=phoff+i*phentsize
        typ,off,vaddr,_,filesz,memsz,flags,align=struct.unpack_from('<IIIIIIII',blob,offset)
        if typ==1: ph.append(dict(offset=off,vaddr=vaddr,filesz=filesz,memsz=memsz,flags=flags,align=align))
    sh=[]
    for i in range(shnum):
        offset=shoff+i*shentsize
        vals=struct.unpack_from('<IIIIIIIIII',blob,offset)
        sh.append(dict(type=vals[1],offset=vals[4],size=vals[5],link=vals[6],entsize=vals[9]))
    syms=[]
    for sec in sh:
        if sec['type']!=11: continue
        strings=sh[sec['link']]; table=blob[strings['offset']:strings['offset']+strings['size']]
        for pos in range(sec['offset'], sec['offset']+sec['size'],sec['entsize']):
            if sec['entsize']<16: break
            name,value,size,info,other,ndx=struct.unpack_from('<IIIBBH',blob,pos)
            if name>=len(table): continue
            end=table.find(b'\0',name)
            if end<0: continue
            word=table[name:end].decode(errors='replace')
            if word in ('dlopen','android_dlopen_ext'):
                syms.append((word,value,ndx,info))
    return ph,syms

def main():
    p=argparse.ArgumentParser()
    p.add_argument('device', nargs='?', default='192.0.2.10:1080')
    args=p.parse_args()
    pid=adb(args.device,'shell','pidof','com.android.bluetooth').strip()
    if not re.fullmatch(r'[1-9][0-9]*',pid): raise ValueError('No single Bluetooth PID: '+repr(pid))
    status=adb(args.device,'shell','su','0','cat',f'/proc/{pid}/status')
    if not re.search(r'^Uid:\s+1002\s',status,re.M) or not re.search(r'^TracerPid:\s+0\s*$',status,re.M):
        raise ValueError('UID/TracerPid guard failed; stopping')
    comm=adb(args.device,'shell','su','0','cat',f'/proc/{pid}/comm').strip()
    if comm!='droid.bluetooth':raise ValueError('Unexpected process name: '+comm)
    maps=adb(args.device,'shell','su','0','cat',f'/proc/{pid}/maps')
    matching=[]
    for line in maps.splitlines():
        m=MAP_RE.match(line)
        if m and m.group(5).strip()==PATH:
            matching.append(dict(start=int(m.group(1),16),end=int(m.group(2),16),perms=m.group(3),off=int(m.group(4),16)))
    if not matching: raise ValueError('No exact APEX libdl mapping')
    out=pathlib.Path('libdl-m3-readonly.so')
    if not out.exists():
        subprocess.run(['adb','-s',args.device,'pull',PATH,str(out)],check=True,stdout=subprocess.DEVNULL)
    ph,syms=parse_elf(out.read_bytes())
    print('=== RetroBox D2b-2d-B read-only ARM32 ELF address validation ===')
    print('Bluetooth PID:',pid,'threads:',re.search(r'^Threads:\s+(\d+)',status,re.M).group(1))
    print('ELF source:',PATH)
    for x in matching: print('MAP: 0x%08x-0x%08x %s file-offset=0x%x'%(x['start'],x['end'],x['perms'],x['off']))
    for x in ph: print('PT_LOAD: vaddr=0x%x offset=0x%x memsz=0x%x flags=%d align=0x%x'%(x['vaddr'],x['offset'],x['memsz'],x['flags'],x['align']))
    if not syms: print('WARNING: dlopen dynamic symbol not found');return 3
    for name,value,ndx,info in syms:
        print('DYNAMIC SYMBOL:',name,'st_value=0x%x'%value,'thumb_bit=%d'%(value&1))
        containing=[x for x in ph if (x['flags']&1) and x['vaddr']<= (value&~1) < x['vaddr']+x['memsz']]
        if len(containing)!=1: print('UNRESOLVED: no unique executable PT_LOAD');continue
        seg=containing[0]
        # Derive the address through matching executable file mapping, not a single-image-base assumption.
        filepos=seg['offset']+((value&~1)-seg['vaddr'])
        viable=[x for x in matching if 'x' in x['perms'] and x['off'] <= filepos < x['off']+(x['end']-x['start'])]
        if len(viable)!=1:
            print('UNRESOLVED: executable mapping/file offset cannot be uniquely associated (filepos=0x%x)'%filepos)
            continue
        x=viable[0];candidate=x['start']+(filepos-x['off'])
        print('CANDIDATE: executable file offset 0x%x -> PC 0x%08x%s'%(filepos,candidate,' (Thumb state)' if value&1 else ''))
        print('WARNING: candidate is NOT remote execution validation; do not invoke in Bluetooth.')
    print('PASS: read-only analysis completed. Bluetooth process was not attached.')
    return 0

if __name__=='__main__':
    try:sys.exit(main() or 0)
    except (OSError,ValueError,subprocess.CalledProcessError,struct.error) as e:
        print('FAIL:',e,file=sys.stderr);sys.exit(1)
