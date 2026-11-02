"""Mock BTM->L2CAP callback contract; offline only, never Bluetooth security."""
from dataclasses import dataclass
from enum import Enum, auto

class Result(Enum):
    SUCCESS=auto()
    SUCCESS_NO_SECURITY=auto()
    CMD_STARTED=auto()
    DELAY_CHECK=auto()
    FAILURE=auto()

@dataclass(frozen=True)
class Ticket:
    epoch:int
    ccb:int

class MockBridge:
    def __init__(self):
        self.epoch=0
        self.live={}
        self.events=[]
    def new_link(self):
        self.epoch+=1
        self.live.clear()
    def disconnect(self):
        self.epoch+=1
        self.live.clear()
    def incoming(self,ccb:int,result:Result,*,callback_inline=False):
        t=Ticket(self.epoch,ccb)
        self.live[ccb]=t
        if result==Result.CMD_STARTED:
            self.events.append(("PENDING",t))
        elif result==Result.DELAY_CHECK:
            self.events.append(("DELAY",t))
        elif callback_inline:
            self.completion(t,result)
        else:
            # Caller path requires callback for completion; return status alone
            # is not permission to synthesize a success.
            self.events.append(("WAIT_CALLBACK",t))
        return t
    def completion(self,t:Ticket,result:Result):
        if self.live.get(t.ccb)!=t or t.epoch!=self.epoch:
            self.events.append(("STALE",t));return False
        if result==Result.DELAY_CHECK:
            self.events.append(("DELAY",t));return False
        if result==Result.CMD_STARTED:
            self.events.append(("INVALID_CALLBACK",t));return False
        self.live.pop(t.ccb)
        self.events.append(("SEC_COMP" if result in (Result.SUCCESS,Result.SUCCESS_NO_SECURITY) else "SEC_COMP_NEG",t))
        return result in (Result.SUCCESS,Result.SUCCESS_NO_SECURITY)
