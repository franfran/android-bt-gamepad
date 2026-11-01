"""Offline DS3 HID Control/Interrupt association prototype.

No Bluetooth security decisions, key generation, HCI commands, or Android
integration. A matching MAC is NOT proof of a legitimate controller.
"""
from dataclasses import dataclass, field

CONTROL = 0x11
INTERRUPT = 0x13

@dataclass
class Session:
    peer_token: str
    host_token: str
    enrolled_by_usb: bool
    owner_approved: bool
    expires_at: int
    revoked: bool = False
    channels: set[int] = field(default_factory=set)
    closed: bool = False

def admit_candidate(s: Session, *, peer: str, host: str, psm: int,
                    inbound: bool, classic: bool, now: int) -> str:
    if s.closed or s.revoked or not s.enrolled_by_usb or not s.owner_approved:
        return "DENY_NOT_AUTHORIZED"
    if now >= s.expires_at:
        s.closed = True
        s.channels.clear()
        return "DENY_EXPIRED"
    if peer != s.peer_token or host != s.host_token:
        return "DENY_IDENTITY_MISMATCH"
    if not inbound or not classic or psm not in (CONTROL, INTERRUPT):
        return "DENY_WRONG_TRANSPORT_OR_PSM"
    if psm in s.channels:
        return "DENY_SAME_CHANNEL_DUPLICATE"
    if psm == INTERRUPT and CONTROL not in s.channels:
        return "DENY_INTERRUPT_BEFORE_CONTROL"
    s.channels.add(psm)
    return "CANDIDATE_ONLY_NOT_AUTHENTICATED"

def complete(s: Session) -> bool:
    return not s.closed and s.channels == {CONTROL, INTERRUPT}

def revoke(s: Session) -> None:
    s.revoked = True
    s.closed = True
    s.channels.clear()
