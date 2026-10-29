#!/usr/bin/env python3
"""Bounded read-only Bluetooth JNI mapping summary; never executes in target."""
import argparse
import json
import re
import subprocess
import sys

def read(serial, command):
    p=subprocess.run(["adb","-s",serial,"exec-out","su","0","sh","-c",command],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12)
    if p.returncode or len(p.stdout)>1048576:
        raise RuntimeError("read-only snapshot unavailable")
    return p.stdout.decode("utf-8","replace").replace("\r","")

def pid(raw):
    val=raw.strip()
    if not re.fullmatch(r"[1-9][0-9]{0,7}",val):
        raise ValueError("ambiguous PID")
    return val

def status(raw):
    fields={}
    for field in ("Pid","Uid","TracerPid"):
        m=re.search(r"^"+field+r":\s*(\d+)",raw,re.M)
        if not m: raise ValueError("missing process status")
        fields[field]=int(m.group(1))
    return fields

def category(path):
    for prefix,name in (("/system_ext/","SYSTEM_EXT"),("/system/","SYSTEM"),
                        ("/product/","PRODUCT"),("/vendor/","VENDOR"),
                        ("/odm/","ODM"),("/apex/","APEX")):
        if path.startswith(prefix): return name
    return "OTHER"

def summarize(maps):
    parts=set()
    for line in maps.splitlines():
        # /proc/PID/maps: address perms offset dev inode optional pathname
        columns=line.split(None,5)
        if len(columns)!=6: continue
        path=columns[5].removesuffix(" (deleted)") if hasattr(str,"removesuffix") else columns[5].replace(" (deleted)","")
        if path.rsplit("/",1)[-1]=="libbluetooth_jni.so":
            parts.add(category(path))
    return {"jni_library_mapped":bool(parts),
            "jni_mapping_partition_categories":sorted(parts)}

def collect(serial):
    if not serial or len(serial)>128 or serial.startswith("-"):
        raise ValueError("invalid ADB serial")
    first=pid(read(serial,"pidof com.android.bluetooth"))
    before=status(read(serial,"cat /proc/"+first+"/status"))
    comm=read(serial,"cat /proc/"+first+"/comm").strip()
    if before["Pid"]!=int(first) or before["Uid"]!=1002 or before["TracerPid"]!=0 or comm!="droid.bluetooth":
        raise ValueError("Bluetooth process identity mismatch")
    maps=read(serial,"cat /proc/"+first+"/maps")
    after=status(read(serial,"cat /proc/"+first+"/status"))
    last=pid(read(serial,"pidof com.android.bluetooth"))
    if first!=last or before!=after:
        raise ValueError("Bluetooth process changed during observation")
    return {"stage":"S7-C4C-3","mode":"READ_ONLY_BLUETOOTH_JNI_MAPPING",
            "identity_verified":True,
            **summarize(maps),
            "jni_load_mechanism":"UNVERIFIED",
            "caller_linker_namespace":"UNVERIFIED",
            "addon_path_permitted":"UNVERIFIED",
            "injection_authorized":False,"decision":"NO_GO"}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adb_serial")
    args=parser.parse_args(argv)
    try: report=collect(args.adb_serial)
    except (RuntimeError,ValueError,OSError,subprocess.TimeoutExpired):
        print(json.dumps({"stage":"S7-C4C-3","mode":"READ_ONLY_BLUETOOTH_JNI_MAPPING",
              "error":"read-only JNI observation unavailable",
              "decision":"NO_GO","injection_authorized":False}),file=sys.stderr)
        return 2
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
