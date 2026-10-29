#!/usr/bin/env python3
"""Bounded read-only map corroboration for fixed M3 JNI DT_NEEDED library names."""
import argparse
import json
import re
import subprocess
import sys

NEEDED=("libbase.so","libc++.so","libc.so","libchrome.so",
        "libdl.so","liblog.so","libm.so","libnativehelper.so")

def read(serial,command):
    p=subprocess.run(["adb","-s",serial,"exec-out","su","0","sh","-c",command],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12)
    if p.returncode or len(p.stdout)>1048576:
        raise ValueError("read unavailable")
    return p.stdout.decode("utf-8","replace")

def pid(s):
    s=s.strip()
    if not re.fullmatch(r"[1-9][0-9]{0,7}",s): raise ValueError("pid ambiguous")
    return s

def status(s):
    v={}
    for k in ("Pid","Uid","TracerPid"):
        m=re.search(r"^"+k+r":\s*(\d+)",s,re.M)
        if not m: raise ValueError("status unavailable")
        v[k]=int(m.group(1))
    return v

def partition(path):
    for prefix,name in (("/system_ext/","SYSTEM_EXT"),("/system/","SYSTEM"),
                        ("/vendor/","VENDOR"),("/product/","PRODUCT"),
                        ("/apex/","APEX"),("/odm/","ODM")):
        if path.startswith(prefix): return name
    return "OTHER"

def summarize(raw):
    found={name:set() for name in NEEDED}
    for line in raw.splitlines():
        cols=line.split(None,5)
        if len(cols)!=6: continue
        path=cols[5]
        if path.endswith(" (deleted)"): path=path[:-10]
        base=path.rsplit("/",1)[-1]
        if base in found: found[base].add(partition(path))
    return [{"library":name,
             "mapped":bool(found[name]),
             "partition_categories":sorted(found[name])} for name in NEEDED]

def collect(serial):
    if not serial or serial.startswith("-") or len(serial)>128: raise ValueError("serial invalid")
    first=pid(read(serial,"pidof com.android.bluetooth"))
    before=status(read(serial,"cat /proc/"+first+"/status"))
    comm=read(serial,"cat /proc/"+first+"/comm").strip()
    if before["Pid"]!=int(first) or before["Uid"]!=1002 or before["TracerPid"]!=0 or comm!="droid.bluetooth":
        raise ValueError("identity mismatch")
    result=summarize(read(serial,"cat /proc/"+first+"/maps"))
    after=status(read(serial,"cat /proc/"+first+"/status"))
    last=pid(read(serial,"pidof com.android.bluetooth"))
    if first!=last or before!=after: raise ValueError("process changed")
    return {"stage":"S7-C4C-3","mode":"READ_ONLY_DEPENDENCY_MAP_CORROBORATION",
            "process_identity_verified":True,"needed_library_map_evidence":result,
            "runtime_dependency_resolution":"UNVERIFIED",
            "caller_linker_namespace":"UNVERIFIED",
            "addon_path_permitted":"UNVERIFIED",
            "injection_authorized":False,"decision":"NO_GO"}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("adb_serial")
    args=ap.parse_args(argv)
    try: out=collect(args.adb_serial)
    except (ValueError,OSError,subprocess.TimeoutExpired):
        print(json.dumps({"stage":"S7-C4C-3","mode":"READ_ONLY_DEPENDENCY_MAP_CORROBORATION",
                          "error":"read-only mapping observation unavailable",
                          "decision":"NO_GO","injection_authorized":False}),file=sys.stderr)
        return 2
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
