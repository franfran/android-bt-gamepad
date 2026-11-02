"""Host-only DS3 policy model. No Bluetooth I/O; NOT production authentication."""
from dataclasses import dataclass
from enum import Enum, auto

class Phase(Enum):
    UNENROLLED = auto()
    ENROLLED = auto()
    ACL = auto()
    CONTROL = auto()
    BOTH_CHANNELS = auto()
    JAVA = auto()
    ACTIVE = auto()

@dataclass(frozen=True)
class Event:
    epoch: int
    enrollment_generation: int
    adapter_generation: int

class CableSession:
    def __init__(self):
        self.phase = Phase.UNENROLLED
        self.enrollment_generation = 0
        self.adapter_generation = 0
        self.epoch = 0
        self.revoked = True

    def enroll(self, *, physical_usb_confirmed: bool, owner_approved: bool):
        if not physical_usb_confirmed or not owner_approved:
            return False
        self.enrollment_generation += 1
        self.revoked = False
        self.phase = Phase.ENROLLED
        return True

    def revoke(self):
        self.enrollment_generation += 1
        self.revoked = True
        self.epoch += 1
        self.phase = Phase.UNENROLLED

    def adapter_changed(self):
        self.adapter_generation += 1
        self.revoke()

    def disconnect(self):
        self.epoch += 1
        self.phase = Phase.UNENROLLED if self.revoked else Phase.ENROLLED

    def connect(self, *, trusted_peer_proven: bool):
        # Symbolic oracle, NOT IMPLEMENTED: real DS3 cryptographic radio proof
        # is not established. Never infer from MAC/name/CoD or USB 0xF5 alone.
        if self.revoked or self.phase != Phase.ENROLLED or not trusted_peer_proven:
            return None
        self.epoch += 1
        self.phase = Phase.ACL
        return Event(self.epoch, self.enrollment_generation, self.adapter_generation)

    def _valid(self, event):
        return (event is not None and not self.revoked
                and event.epoch == self.epoch
                and event.enrollment_generation == self.enrollment_generation
                and event.adapter_generation == self.adapter_generation)

    def channel(self, event, *, psm: int):
        if not self._valid(event):
            return False
        if psm == 0x11 and self.phase == Phase.ACL:
            self.phase = Phase.CONTROL
            return True
        if psm == 0x13 and self.phase == Phase.CONTROL:
            self.phase = Phase.BOTH_CHANNELS
            return True
        return False

    def java_admit(self, event, *, quiet: bool = False, forbidden: bool = False):
        if not self._valid(event) or self.phase != Phase.BOTH_CHANNELS or quiet or forbidden:
            return False
        self.phase = Phase.JAVA
        return True

    def uhid_ready(self, event, *, report_completion_verified: bool):
        if not self._valid(event) or self.phase != Phase.JAVA or not report_completion_verified:
            return False
        self.phase = Phase.ACTIVE
        return True
