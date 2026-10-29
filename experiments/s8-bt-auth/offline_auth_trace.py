#!/usr/bin/env python3
"""Offline read-only DS3 HID->HCI auth chronology, never emits addresses or secrets."""
import argparse
import json
from pathlib import Path
import struct
import sys

MAX_BYTES = 8 * 1024 * 1024
MAX_ATTEMPTS = 16
MAX_RECORDS = 100000

class TraceError(ValueError):
    pass

def decode(data):
    if len(data) < 16 or len(data) > MAX_BYTES or data[:8] != b"btsnoop\x00":
        raise TraceError("invalid or oversized btsnoop")
    version, datalink = struct.unpack_from(">II", data, 8)
    if version != 1 or datalink != 1002:
        raise TraceError("unsupported btsnoop version or datalink")
    pos = 16
    idx = 0
    while pos < len(data):
        if pos + 24 > len(data):
            raise TraceError("truncated record header")
        original, size, flags, drops, stamp = struct.unpack_from(">IIIIQ", data, pos)
        pos += 24
        if size > original or size > len(data) - pos:
            raise TraceError("truncated or malformed record")
        packet = data[pos:pos+size]
        pos += size
        idx += 1
        if idx > MAX_RECORDS:
            raise TraceError("too many records")
        if len(packet) < 2:
            continue
        t = packet[0]
        if t == 1 and len(packet) >= 4:
            opcode = int.from_bytes(packet[1:3], "little")
            plen = packet[3]
            if plen != len(packet) - 4:
                continue
            args = packet[4:]
            kind = {0x0411:"auth_request",0x040c:"key_negative",
                    0x040d:"pin_reply",0x040e:"pin_negative"}.get(opcode)
            if kind is not None:
                if kind == "auth_request" and len(args) >= 2:
                    yield idx,kind,{"handle":int.from_bytes(args[:2],"little")}
                elif kind != "auth_request" and len(args) >= 6:
                    yield idx,kind,{"addr":args[:6]}
        elif t == 4 and len(packet) >= 3:
            code = packet[1]
            plen = packet[2]
            if plen != len(packet) - 3:
                continue
            args = packet[3:]
            if code == 0x03 and len(args) >= 11 and args[0] == 0:
                yield idx,"connection_complete",{
                    "handle":int.from_bytes(args[1:3],"little"),"addr":args[3:9]}
            elif code in (0x17,0x16,0x18) and len(args) >= 6:
                kind={0x17:"key_request",0x16:"pin_request",0x18:"key_notification"}[code]
                yield idx,kind,{"addr":args[:6]}
            elif code == 0x06 and len(args) >= 3:
                yield idx,"auth_complete",{
                    "status":args[0],"handle":int.from_bytes(args[1:3],"little")}
            elif code == 0x05 and len(args) >= 4:
                yield idx,"disconnect",{
                    "handle":int.from_bytes(args[1:3],"little"),"reason":args[3]}
        elif t == 2 and len(packet) >= 13:
            hf=int.from_bytes(packet[1:3],"little")
            length=int.from_bytes(packet[3:5],"little")
            if length != len(packet)-5 or ((hf >> 12) & 3) not in (0,2):
                continue
            payload=packet[5:]
            l2len=int.from_bytes(payload[0:2],"little")
            cid=int.from_bytes(payload[2:4],"little")
            if cid != 1 or l2len > len(payload)-4:
                continue
            sig=payload[4:4+l2len]
            if len(sig) >= 8 and sig[0] == 2:
                siglen=int.from_bytes(sig[2:4],"little")
                psm=int.from_bytes(sig[4:6],"little")
                if siglen >= 4 and psm == 0x0011:
                    yield idx,"hid_control_request",{"handle":hf & 0x0fff}

def analyze(data):
    connections = {}
    attempts=[]
    for idx,kind,v in decode(data):
        if kind=="connection_complete":
            connections[v["handle"]]=v["addr"]
            continue
        if kind=="hid_control_request":
            if len(attempts)<MAX_ATTEMPTS:
                attempts.append({"handle":v["handle"],"addr":connections.get(v["handle"]),
                                 "record":idx,"auth_request":False,"key_request":False,
                                 "key_negative":False,"pin_request":False,
                                 "pin_reply_sent":False,"key_notification":False,
                                 "status":None,"disconnect":None})
            continue
        handle=v.get("handle")
        if kind=="auth_request":
            matches=[a for a in attempts if a["handle"]==handle and a["status"] is None]
            if matches:
                matches[-1]["auth_request"]=True
            continue
        if kind in ("auth_complete","disconnect"):
            matches=[a for a in attempts if a["handle"]==handle]
            if matches:
                a=matches[-1]
                if kind=="auth_complete" and a["auth_request"]:
                    a["status"]=v["status"]
                if kind=="disconnect" and a["auth_request"]:
                    a["disconnect"]=v["reason"]
            continue
        # Link Key / PIN HCI events carry peer address, not ACL handle.
        eligible=[a for a in attempts if a["auth_request"] and a["status"] is None
                  and (a["addr"] is None or a["addr"]==v["addr"])]
        if len(eligible)!=1:
            continue  # ambiguity: don't attribute another device's pairing
        a=eligible[0]
        if a["addr"] is None:
            a["addr"]=v["addr"]
        if kind=="key_request":a["key_request"]=True
        elif kind=="key_negative" and a["key_request"]:a["key_negative"]=True
        elif kind=="pin_request":a["pin_request"]=True
        elif kind=="pin_reply" and a["pin_request"]:a["pin_reply_sent"]=True
        elif kind=="key_notification":a["key_notification"]=True
    result=[]
    for a in attempts:
        status=a["status"]
        outcome=("AUTH_TIMEOUT_0X22" if status==0x22 else
                 "AUTH_SUCCESS_REPORTED" if status==0 else
                 "OTHER_AUTH_FAILURE" if status is not None else
                 "NO_AUTH_COMPLETION_OBSERVED")
        result.append({"hid_control_record":a["record"],
                       "auth_requested":a["auth_request"],"link_key_requested":a["key_request"],
                       "link_key_negative_reply":a["key_negative"],
                       "pin_requested":a["pin_request"],"pin_reply_command_seen":a["pin_reply_sent"],
                       "link_key_notification_seen":a["key_notification"],
                       "authentication_status":("0x%02x"%status if status is not None else "UNOBSERVED"),
                       "disconnect_reason":("0x%02x"%a["disconnect"] if a["disconnect"] is not None else "UNOBSERVED"),
                       "outcome":outcome})
    return {"mode":"OFFLINE_HCI_HID_AUTH_REVIEW","stage":"S8",
            "attempts":result,
            "runtime_callsite":"UNVERIFIED",
            "cause_of_timeout":"UNVERIFIED",
            "note":"PIN reply command presence is not proof of authentication or peer receipt",
            "injection_authorized":False,"decision":"NO_GO"}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("local_btsnoop",help="Private local capture: never upload or commit")
    args=ap.parse_args(argv)
    try:
        file=Path(args.local_btsnoop)
        if file.stat().st_size>MAX_BYTES:
            raise TraceError("oversize")
        report=analyze(file.read_bytes())
    except (OSError,TraceError,ValueError,struct.error):
        print(json.dumps({"stage":"S8","mode":"OFFLINE_HCI_HID_AUTH_REVIEW",
                          "error":"offline trace unavailable or malformed",
                          "decision":"NO_GO","injection_authorized":False}),file=sys.stderr)
        return 2
    print(json.dumps(report,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    sys.exit(main())
