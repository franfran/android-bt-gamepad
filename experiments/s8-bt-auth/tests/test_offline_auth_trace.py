import importlib.util
import json
from pathlib import Path
import struct
import unittest

path=Path(__file__).resolve().parents[1]/"offline_auth_trace.py"
spec=importlib.util.spec_from_file_location("offline_auth_trace",path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

ADDR=bytes.fromhex("010203040506")
OTHER=bytes.fromhex("102030405060")
HANDLE=0x0080

def cmd(op,args=b""):
    return b"\x01"+struct.pack("<HB",op,len(args))+args

def event(code,args=b""):
    return b"\x04"+bytes([code,len(args)])+args

def conn(addr=ADDR,handle=HANDLE):
    return event(3,b"\x00"+struct.pack("<H",handle)+addr+b"\x01\x00")

def hid(handle=HANDLE):
    sig=b"\x02\x01"+struct.pack("<H",4)+struct.pack("<HH",0x0011,0x06f5)
    l2=struct.pack("<HH",len(sig),1)+sig
    return b"\x02"+struct.pack("<HH",0x2000|handle,len(l2))+l2

def capture(*packets):
    head=b"btsnoop\x00"+struct.pack(">II",1,1002)
    return head+b"".join(struct.pack(">IIIIQ",len(p),len(p),0,0,0)+p for p in packets)

def flow(addr=ADDR,reply=True,status=0x22,handle=HANDLE):
    parts=[conn(addr,handle),hid(handle),cmd(0x0411,struct.pack("<H",handle)),
           event(0x17,addr),cmd(0x040c,addr),event(0x16,addr)]
    if reply:
        parts.append(cmd(0x040d,addr+b"\x06"+addr))
    parts.extend([event(0x06,bytes([status])+struct.pack("<H",handle)),
                 event(0x05,b"\x00"+struct.pack("<H",handle)+bytes([status]))])
    return parts

class OfflineAuthTests(unittest.TestCase):
    def test_historical_timeout_sequence(self):
        result=mod.analyze(capture(*flow()))
        self.assertEqual(len(result["attempts"]),1)
        a=result["attempts"][0]
        self.assertEqual(a["outcome"],"AUTH_TIMEOUT_0X22")
        self.assertTrue(a["pin_reply_command_seen"])
        self.assertTrue(a["link_key_negative_reply"])
        self.assertEqual(a["disconnect_reason"],"0x22")
        self.assertEqual(result["runtime_callsite"],"UNVERIFIED")
        self.assertFalse(result["injection_authorized"])

    def test_second_attempt_without_pin_reply(self):
        first=flow()
        second=flow(reply=False,handle=0x81)
        report=mod.analyze(capture(*(first+second)))
        self.assertEqual(len(report["attempts"]),2)
        self.assertFalse(report["attempts"][1]["pin_reply_command_seen"])
        self.assertEqual(report["attempts"][1]["outcome"],"AUTH_TIMEOUT_0X22")

    def test_success_status_does_not_mean_hid_success(self):
        a=mod.analyze(capture(*flow(status=0)))["attempts"][0]
        self.assertEqual(a["outcome"],"AUTH_SUCCESS_REPORTED")
        self.assertNotIn("HID_CONNECTED",str(a))

    def test_no_auth_complete_is_not_failure(self):
        a=mod.analyze(capture(*flow()[:-2]))["attempts"][0]
        self.assertEqual(a["outcome"],"NO_AUTH_COMPLETION_OBSERVED")

    def test_wrong_addr_pin_not_assigned(self):
        parts=flow()
        parts[5]=event(0x16,OTHER)
        parts[6]=cmd(0x040d,OTHER+b"\x06"+OTHER)
        a=mod.analyze(capture(*parts))["attempts"][0]
        self.assertFalse(a["pin_requested"])
        self.assertFalse(a["pin_reply_command_seen"])

    def test_wrong_handle_auth_not_assigned(self):
        parts=flow()
        parts[2]=cmd(0x0411,struct.pack("<H",0x77))
        a=mod.analyze(capture(*parts))["attempts"][0]
        self.assertFalse(a["auth_requested"])
        self.assertEqual(a["authentication_status"],"UNOBSERVED")

    def test_does_not_emit_address_or_secret(self):
        report=json.dumps(mod.analyze(capture(*flow())))
        for marker in ("010203040506","01:02:03:04:05:06","123456"):
            self.assertNotIn(marker,report)
        self.assertNotIn("pin_bytes",report)

    def test_fail_closed_invalid_file(self):
        with self.assertRaises(mod.TraceError):
            list(mod.decode(b"fake"))
        with self.assertRaises(mod.TraceError):
            list(mod.decode(capture(*flow())[:-2]))

if __name__=="__main__":
    unittest.main()
