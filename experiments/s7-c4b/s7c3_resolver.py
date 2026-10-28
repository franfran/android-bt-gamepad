#!/usr/bin/env python3
"""S7-C3: read-only Bluetooth ELF address and identity validator. NO injection code."""
import argparse, hashlib, json, re, struct, subprocess, sys
from pathlib import Path
LIB='/apex/com.android.runtime/lib/bionic/libdl.so'

def adb(serial,command,binary=False):
    p=subprocess.run(['adb','-s',serial,'shell', 'su 0 '+command],capture_output=True,timeout=20)
    if p.returncode: raise RuntimeError('ADB command failed: '+p.stderr.decode(errors='replace')[:250])
    return p.stdout if binary else p.stdout.decode(errors='replace').replace('\r','').replace('\x00','')

def maps_parse(s):
    rows=[]
    for line in s.splitlines():
        m=re.match(r'^([0-9a-f]+)-([0-9a-f]+)\s+([rwxps-]{4})\s+([0-9a-f]+)\s+\S+\s+\d+\s*(.*)$',line)
        if m: rows.append(dict(start=int(m[1],16),end=int(m[2],16),perm=m[3],offset=int(m[4],16),path=m[5].strip()))
    return rows

def elf32(data):
    if data[:4]!=b'\x7fELF' or data[4]!=1 or data[5]!=1 or data[18:20]!=b'\x28\x00':raise ValueError('expected ARM32 little-endian ELF')
    if len(data)<52: raise ValueError('truncated ELF')
    phoff, shoff=struct.unpack_from('<II',data,28)
    phents,phnum,shents,shnum=struct.unpack_from('<HHHH',data,42)
    def slc(off,size):
        if off<0 or size<0 or off+size>len(data):raise ValueError('ELF offset out of bounds')
        return data[off:off+size]
    loads=[]
    for i in range(phnum):
        o=phoff+i*phents
        slc(o,32)
        p_type,p_off,p_vaddr,_,_,p_memsz,p_flags,p_align=struct.unpack_from('<IIIIIIII',data,o)
        if p_type==1:loads.append(dict(offset=p_off,vaddr=p_vaddr,memsz=p_memsz,flags=p_flags,align=p_align))
    sections=[]
    for i in range(shnum):
        o=shoff+i*shents;slc(o,40)
        q=struct.unpack_from('<IIIIIIIIII',data,o)
        sections.append(dict(type=q[1],offset=q[4],size=q[5],link=q[6],entsize=q[9]))
    symbols={}
    for sec in sections:
        if sec['type']!=11 or not sec['entsize'] or sec['link']>=len(sections):continue
        strings=sections[sec['link']];strtab=slc(strings['offset'],strings['size'])
        for o in range(sec['offset'],sec['offset']+sec['size'],sec['entsize']):
            slc(o,16)
            name,value,size,info,other,shndx=struct.unpack_from('<IIIBBH',data,o)
            if name>=len(strtab):continue
            end=strtab.find(b'\x00',name)
            if end<0: continue
            n=strtab[name:end].decode(errors='replace')
            if n in ('dlopen','android_dlopen_ext') and value and shndx:
                symbols[n]=value
    return loads,symbols

def resolve(rows,loads,sym,path=LIB):
    entries=[r for r in rows if r['path']==path]
    if not entries:raise ValueError('missing exact libdl mapping')
    # Android/Bionic may report file offset 0 for ALL tiny libdl.so
    # mappings. File-offset == 0 is not a unique base selector.
    # Determine load bias from the lowest mapping, then validate each
    # PT_LOAD's page coverage and permissions rather than trusting offsets.
    entries=sorted(entries,key=lambda r:r['start'])
    base=entries[0]['start']
    if entries[0]['offset']!=0 or 'r' not in entries[0]['perm']:
        raise ValueError('libdl first mapping is not readable offset-zero header')
    if not any(s['vaddr'] == 0 and s['offset'] == 0 and not (s['flags'] & 1) for s in loads):
        raise ValueError('no PT_LOAD header at zero virtual address')
    # Bionic may have non-executable PT_LOADs absent from file-backed
    # /proc/maps (e.g. anonymous BSS / RELRO mappings). Those segments
    # are irrelevant to resolving an exported executable function.
    # Verify the containing executable PT_LOAD and its mapped pages below.
    code=sym&~1;addr=base+code
    executable=[r for r in entries if 'x' in r['perm'] and r['start']<=addr<r['end']]
    if len(executable)!=1:raise ValueError('resolved symbol outside executable libdl range')
    segs=[s for s in loads if s['flags']&1 and s['vaddr']<=code<s['vaddr']+s['memsz']]
    if len(segs)!=1:raise ValueError('symbol not in executable PT_LOAD')
    s=segs[0]
    if not (base+s['vaddr'] <= addr < base+s['vaddr']+s['memsz']):
        raise ValueError('symbol virtual address mismatch')
    fileoffset=s['offset']+code-s['vaddr']
    if not (0<=fileoffset):raise ValueError('invalid symbol file offset')
    return dict(load_bias=hex(base),instruction_address=hex(addr),thumb_function_pointer=hex(addr|(sym&1)),file_offset=hex(fileoffset))

def evaluate(pid,comm,status,rows,loads,syms,pid_after):
    blockers=[]
    uid=re.search(r'^Uid:\s+(\d+)',status,re.M);tracer=re.search(r'^TracerPid:\s+(\d+)',status,re.M)
    if comm.strip()!='droid.bluetooth':blockers.append('unexpected process name')
    if not uid or uid[1]!='1002':blockers.append('unexpected UID')
    if not tracer or tracer[1]!='0':blockers.append('tracer already attached')
    if str(pid)!=pid_after.strip():blockers.append('PID changed during inspection')
    if any('libretrobox_ds3_addon.so' in r['path'] for r in rows):blockers.append('addon already mapped')
    targets={}
    for name in ['dlopen','android_dlopen_ext']:
        if name not in syms:blockers.append('missing ELF dynamic symbol: '+name);continue
        try:targets[name]=resolve(rows,loads,syms[name])
        except ValueError as e:blockers.append(f'{name}: {e}')
    return targets,blockers

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('device',nargs='?',help='ADB serial')
    p.add_argument('--maps',type=Path,help='offline /proc/PID/maps fixture')
    p.add_argument('--elf',type=Path,help='offline libdl.so')
    p.add_argument('--pid',type=int,default=675,help='offline fixture PID only')
    p.add_argument('--json-out',type=Path,default=Path('s7c3-evidence.json'))
    a=p.parse_args()
    if not a.device and not(a.maps and a.elf):p.error('provide DEVICE or --maps and --elf')
    output={'stage':'S7-C3','mode':'READ_ONLY','injection_authorized':False,'blockers':[]}
    try:
        if a.maps:
            raw_maps=a.maps.read_text(); raw_elf=a.elf.read_bytes();pid=a.pid
            status='Uid:\t1002\nTracerPid:\t0\n';comm='droid.bluetooth';after=str(pid)
        else:
            serial=a.device
            ps=adb(serial,'pidof com.android.bluetooth').split()
            if len(ps)!=1 or not ps[0].isdigit():raise ValueError('ambiguous Bluetooth PID')
            pid=int(ps[0]);status=adb(serial,f'cat /proc/{pid}/status');comm=adb(serial,f'cat /proc/{pid}/comm')
            raw_maps=adb(serial,f'cat /proc/{pid}/maps')
            # ADB shell binary data through transport; no /tmp file dependency.
            raw_elf=adb(serial,'cat '+LIB,binary=True)
            after=adb(serial,'pidof com.android.bluetooth')
        rows=maps_parse(raw_maps);loads,syms=elf32(raw_elf)
        targets,issues=evaluate(pid,comm,status,rows,loads,syms,after)
        output.update(pid=pid,libdl_sha256=hashlib.sha256(raw_elf).hexdigest(),symbols=targets,inspection_issues=issues)
        output['blockers']+=issues
    except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as e:
        output['blockers'].append('INSPECTION FAILURE: '+str(e))
    output['blockers']+=['Bluetooth linker namespace acceptance not demonstrated',
         'Linker-lock contention and interrupted dlopen recovery not proven safe',
         'Target-specific loader not authorized for injection']
    a.json_out.write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
    print(json.dumps(output,indent=2,sort_keys=True))
    print('INJECTION_GATE=NO-GO (hard coded; no injection capability in this program)')
    return 2 if any(x.startswith('INSPECTION FAILURE') for x in output['blockers']) else 0
if __name__=='__main__':sys.exit(main())
