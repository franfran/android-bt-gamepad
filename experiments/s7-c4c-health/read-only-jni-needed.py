#!/usr/bin/env python3
"""Read-only ELF32 DT_NEEDED inspection of fixed system Bluetooth JNI library."""
import argparse
import json
import re
import struct
import subprocess
import sys

PATH="/system/lib/libbluetooth_jni.so"
MAX_SIZE=16*1024*1024

def needed(data):
    if len(data)<52 or data[:4]!=b"\x7fELF" or data[4:7]!=b"\x01\x01\x01":
        raise ValueError("not little-endian ELF32")
    h=struct.unpack_from("<HHIIIIIHHHHHH",data,16)
    phoff,phentsize,phnum=h[4],h[8],h[9]
    if phentsize<32 or phnum>128 or phoff+phentsize*phnum>len(data):
        raise ValueError("invalid program headers")
    loads=[]; dynamics=[]
    for i in range(phnum):
        p=struct.unpack_from("<IIIIIIII",data,phoff+i*phentsize)
        typ,off,va,_,filesz,memsz,_,_=p
        if off+filesz>len(data): raise ValueError("invalid segment bounds")
        if typ==1: loads.append((va,off,filesz))
        if typ==2: dynamics.append((off,filesz))
    if len(dynamics)!=1: raise ValueError("dynamic segment ambiguous")
    off,length=dynamics[0]
    if length%8: raise ValueError("bad dynamic size")
    entries=[struct.unpack_from("<II",data,off+i) for i in range(0,length,8)]
    terminated=next((i for i,(tag,_) in enumerate(entries) if tag==0),None)
    if terminated is None: raise ValueError("unterminated dynamic table")
    entries=entries[:terminated]
    strtabs=[v for tag,v in entries if tag==5]
    strszs=[v for tag,v in entries if tag==10]
    if len(strtabs)!=1 or len(strszs)!=1 or strszs[0]>1048576:
        raise ValueError("dynamic string table ambiguous")
    addr,size=strtabs[0],strszs[0]
    candidates=[offset+(addr-va) for va,offset,n in loads if va<=addr and addr+size<=va+n]
    if len(candidates)!=1: raise ValueError("strtab address unresolved")
    start=candidates[0]
    names=[]
    for tag,index in entries:
        if tag!=1: continue
        if index>=size: raise ValueError("needed name outside strtab")
        end=data.find(b"\x00",start+index,start+size)
        if end<0: raise ValueError("unterminated needed name")
        name=data[start+index:end].decode("ascii")
        if not re.fullmatch(r"[A-Za-z0-9_.+\-]{1,128}\.so(?:\.[0-9]+)*",name):
            raise ValueError("unexpected library name")
        names.append(name)
    if len(names)>256: raise ValueError("too many dependencies")
    return sorted(set(names))

def inspect(serial):
    if not serial or len(serial)>128 or serial.startswith("-"):
        raise ValueError("invalid ADB serial")
    p=subprocess.run(["adb","-s",serial,"exec-out","su","0","sh","-c","cat "+PATH],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
    if p.returncode or not p.stdout or len(p.stdout)>MAX_SIZE:
        raise ValueError("fixed library read unavailable")
    return {"stage":"S7-C4C-3","mode":"READ_ONLY_JNI_ELF_NEEDED",
            "elf_format":"ELF32_LE","library":"libbluetooth_jni.so",
            "needed_libraries":needed(p.stdout),
            "dependencies_resolved_at_runtime":"UNVERIFIED",
            "caller_linker_namespace":"UNVERIFIED",
            "addon_path_permitted":"UNVERIFIED",
            "injection_authorized":False,"decision":"NO_GO"}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("adb_serial")
    args=ap.parse_args(argv)
    try: report=inspect(args.adb_serial)
    except (ValueError,UnicodeError,struct.error,OSError,subprocess.TimeoutExpired):
        print(json.dumps({"stage":"S7-C4C-3","mode":"READ_ONLY_JNI_ELF_NEEDED",
                          "error":"read-only ELF inspection unavailable",
                          "injection_authorized":False,"decision":"NO_GO"}),file=sys.stderr)
        return 2
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
