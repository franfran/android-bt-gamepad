#!/usr/bin/env python3
"""Read-only M3 Bluetooth executable provenance; no process manipulation."""
import argparse
import json
import re
import subprocess
import sys

def read(serial, cmd):
    p=subprocess.run(["adb","-s",serial,"exec-out","su","0","sh","-c",cmd],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=12)
    if p.returncode or len(p.stdout)>8192:
        raise RuntimeError("read-only evidence unavailable")
    return p.stdout.decode("utf-8","replace").replace("\r","").replace("\x00","").strip()

def decimal(x):
    if not re.fullmatch(r"[1-9][0-9]{0,7}",x): raise ValueError("ambiguous process ID")
    return x

def status(raw):
    data={}
    for name in ("Pid","PPid","Uid","TracerPid","Threads"):
        match=re.search(r"^"+name+r":\s*(\d+)",raw,re.M)
        if not match: raise ValueError("incomplete process status")
        data[name]=int(match.group(1))
    return data

def exe_class(path):
    # Readlink evidence is never emitted. Keep coarse categories only.
    path=path[:-10] if path.endswith(" (deleted)") else path
    if path in ("/system/bin/app_process32","/system/bin/app_process64",
                "/system/bin/app_process"):
        return "APP_PROCESS_BINARY"
    if re.fullmatch(r"/(?:system|system_ext|vendor|product|odm)/bin/[A-Za-z0-9_.-]+",path):
        return "PARTITION_NATIVE_BINARY"
    return "UNKNOWN"

def gather(serial):
    if not serial or len(serial)>128 or serial.startswith("-"):
        raise ValueError("invalid serial")
    first=decimal(read(serial,"pidof com.android.bluetooth"))
    s1=status(read(serial,"cat /proc/"+first+"/status"))
    comm=read(serial,"cat /proc/"+first+"/comm")
    if comm!="droid.bluetooth" or s1["Pid"]!=int(first) or s1["Uid"]!=1002 or s1["TracerPid"]!=0:
        raise ValueError("Bluetooth identity mismatch")
    parent=decimal(str(s1["PPid"]))
    parent_status=status(read(serial,"cat /proc/"+parent+"/status"))
    if parent_status["Pid"]!=int(parent): raise ValueError("parent mismatch")
    target_exe=exe_class(read(serial,"readlink /proc/"+first+"/exe"))
    parent_exe=exe_class(read(serial,"readlink /proc/"+parent+"/exe"))
    s2=status(read(serial,"cat /proc/"+first+"/status"))
    if decimal(read(serial,"pidof com.android.bluetooth"))!=first:
        raise ValueError("PID changed")
    if any(s1[k]!=s2[k] for k in ("Pid","PPid","Uid","TracerPid")):
        raise ValueError("target status changed")
    return {
        "stage":"S7-C4C-3","mode":"READ_ONLY_EXECUTABLE_PROVENANCE",
        "identity_verified":True,"parent_reference_stable":True,
        "bluetooth_executable_category":target_exe,
        "parent_executable_category":parent_exe,
        "launch_mechanism":"UNVERIFIED","caller_linker_namespace":"UNVERIFIED",
        "addon_path_permitted":"UNVERIFIED",
        "injection_authorized":False,"decision":"NO_GO"
    }

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("adb_serial")
    args=ap.parse_args(argv)
    try: report=gather(args.adb_serial)
    except (RuntimeError,ValueError,subprocess.TimeoutExpired,OSError):
        print(json.dumps({"stage":"S7-C4C-3","mode":"READ_ONLY_EXECUTABLE_PROVENANCE",
                          "decision":"NO_GO","injection_authorized":False,
                          "error":"read-only evidence unavailable"}),file=sys.stderr)
        return 2
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
