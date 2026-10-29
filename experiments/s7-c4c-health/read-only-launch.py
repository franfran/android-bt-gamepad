#!/usr/bin/env python3
"""Bounded, read-only Android Bluetooth launch-provenance classification."""
import argparse
import json
import re
import subprocess
import sys

def adb_read(serial, command):
    p = subprocess.run(["adb","-s",serial,"exec-out","su","0","sh","-c",command],
                       stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12)
    if p.returncode or len(p.stdout)>65536:
        raise RuntimeError("read-only process observation unavailable")
    return p.stdout.decode("utf-8","replace").replace("\r","").replace("\x00","")

def pid(value):
    s=value.strip()
    if not re.fullmatch(r"[1-9][0-9]{0,7}",s):
        raise ValueError("missing or ambiguous PID")
    return s

def parse_status(text):
    values={}
    for name in ("Pid","PPid","Uid","Threads","TracerPid"):
        m=re.search(r"^"+name+r":\s*(\d+)",text,re.M)
        if not m: raise ValueError("missing status field")
        values[name]=int(m.group(1))
    return values

def classify(status, parent_comm):
    # Classify only direct-parent evidence, not classloader namespace.
    if parent_comm in ("zygote","zygote64","usap32","usap64"):
        return "ZYGOTE_PARENT_OBSERVED"
    if parent_comm and parent_comm not in ("UNKNOWN",""):
        return "NON_ZYGOTE_PARENT_OBSERVED"
    return "UNKNOWN"

def collect(serial):
    if not serial or len(serial)>128 or serial.startswith("-"):
        raise ValueError("invalid ADB serial")
    first=pid(adb_read(serial,"pidof com.android.bluetooth"))
    comm=adb_read(serial,"cat /proc/"+first+"/comm").strip()
    status=parse_status(adb_read(serial,"cat /proc/"+first+"/status"))
    if comm!="droid.bluetooth" or status["Uid"]!=1002 or status["Pid"]!=int(first):
        raise ValueError("Bluetooth identity mismatch")
    if status["TracerPid"]!=0: raise ValueError("process already traced")
    parent=str(status["PPid"])
    if not re.fullmatch(r"[1-9][0-9]{0,7}",parent):
        raise ValueError("ambiguous parent PID")
    parent_status=parse_status(adb_read(serial,"cat /proc/"+parent+"/status"))
    if parent_status["Pid"]!=int(parent):
        raise ValueError("parent identity changed")
    parent_comm=adb_read(serial,"cat /proc/"+parent+"/comm").strip()
    last=pid(adb_read(serial,"pidof com.android.bluetooth"))
    again=parse_status(adb_read(serial,"cat /proc/"+first+"/status"))
    if last!=first or again["Pid"]!=status["Pid"] or again["PPid"]!=status["PPid"] or again["Uid"]!=status["Uid"]:
        raise ValueError("Bluetooth process changed during observation")
    return {
        "stage":"S7-C4C-3","mode":"READ_ONLY_LAUNCH_PROVENANCE",
        "identity_verified":True,"parent_relationship_stable":True,
        "parent_classification":classify(status,parent_comm),
        "threads":status["Threads"],
        "caller_linker_namespace":"UNVERIFIED",
        "launch_namespace":"UNVERIFIED",
        "addon_path_permitted":"UNVERIFIED",
        "injection_authorized":False,"decision":"NO_GO"
    }

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("adb_serial")
    args=ap.parse_args(argv)
    try: result=collect(args.adb_serial)
    except (RuntimeError,ValueError,subprocess.TimeoutExpired,OSError):
        print(json.dumps({"stage":"S7-C4C-3","mode":"READ_ONLY_LAUNCH_PROVENANCE",
                          "error":"read-only observation failed","decision":"NO_GO",
                          "injection_authorized":False}),file=sys.stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
