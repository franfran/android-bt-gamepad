#!/usr/bin/env python3
"""Plan and optionally inspect Thumb veneer candidates using an OFFLINE local M3 ELF.

The archived callgraph gives BLX immediate targets; this tool cannot infer
whether they are PLT, veneer or implementation without the original ELF.
No ADB/device functionality, memory writes, or patching.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

MAX_TEXT = 2 * 1024 * 1024
MAX_ELF = 64 * 1024 * 1024
WINDOW = 32
FUNC = re.compile(r"^FUNCTION (\S+): 0x[0-9a-f]+ size=\d+")
CALL = re.compile(r"^\s*(0x[0-9a-f]+)\s+blx\s+(0x[0-9a-f]+)\s+->\s+unresolved\s*$")

def candidates(text, needle="hidh_l2cif_connect_ind"):
    current=""
    result={}
    for line in text.splitlines():
        match=FUNC.match(line)
        if match:
            current=match.group(1)
            continue
        call=CALL.match(line)
        if call and needle in current:
            site=int(call.group(1),16)
            target=int(call.group(2),16)
            if 0x27ee28 <= site < 0x27f0f8:
                result.setdefault(target,[]).append(site)
    return [{"target_vma":hex(addr),
             "callsite_vmas":[hex(site) for site in sites],
             "classification":"UNRESOLVED_DISPATCH_TARGET"}
            for addr,sites in sorted(result.items())]

def inspect(callgraph, elf=None, objdump="llvm-objdump"):
    items=candidates(callgraph)
    if not items:
        raise ValueError("no recorded unresolved HID callback branches")
    result={"mode":"OFFLINE_THUMB_DISPATCH_REVIEW","stage":"S8",
            "target_type":"UNVERIFIED_WITHOUT_DISASSEMBLY",
            "candidates":items,"source":"ARCHIVED_M3_CALLGRAPH",
            "callback_resolution":"UNVERIFIED",
            "security_path_proven":False,
            "decision":"NO_GO","injection_authorized":False}
    if elf is None:
        return result
    elf=Path(elf)
    if not elf.is_file() or not 0<elf.stat().st_size<=MAX_ELF:
        raise ValueError("missing or oversized offline ELF")
    # Only fixed, small readonly target windows. No unbounded process output.
    for item in items:
        addr=int(item["target_vma"],16)
        proc=subprocess.run([objdump,"-d","--triple=thumbv7-linux-androideabi",
                             "--start-address=0x%x"%addr,
                             "--stop-address=0x%x"%(addr+WINDOW),str(elf)],
                            capture_output=True,text=True,timeout=10,check=False)
        if proc.returncode != 0 or len(proc.stdout)>20000:
            raise ValueError("disassembler failed")
        # Do not label as PLT/veneer from proximity or text alone.
        # Return architecture-neutral mnemonic lines for operator verification.
        instructions=[]
        for line in proc.stdout.splitlines():
            m=re.match(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f ]+\s+)?([a-z][a-z0-9.]+)\s*(.*)$",line)
            if m and addr<=int(m.group(1),16)<addr+WINDOW:
                instructions.append({"offset":m.group(1),"opcode":m.group(2),
                                     "operand":m.group(3)[:120]})
        item["bounded_instructions"]=instructions[:16]
        item["classification"]="DISASSEMBLY_AVAILABLE_REVIEW_REQUIRED" if instructions else "NO_INSTRUCTIONS"
    result["target_type"]="DISASSEMBLY_AVAILABLE_REVIEW_REQUIRED"
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("callgraph",help="archived callgraph text")
    ap.add_argument("--elf",help="optional private local M3 libbluetooth.so (never commit)")
    args=ap.parse_args()
    try:
        path=Path(args.callgraph)
        if path.stat().st_size>MAX_TEXT:
            raise ValueError("oversized callgraph")
        report=inspect(path.read_text(encoding="utf-8"),args.elf)
    except (OSError,UnicodeError,ValueError,subprocess.TimeoutExpired):
        print(json.dumps({"mode":"OFFLINE_THUMB_DISPATCH_REVIEW",
                          "error":"offline evidence unavailable or inconsistent",
                          "decision":"NO_GO","injection_authorized":False}),file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True,indent=2))
    return 0

if __name__=="__main__":
    sys.exit(main())
