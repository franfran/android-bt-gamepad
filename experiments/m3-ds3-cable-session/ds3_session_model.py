"""Host-only bounded-risk DS3 policy model; no real Bluetooth or crypto validation."""
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
        self.risk_approved = False
        self.enrolled_claim = None
        self.descriptor_allowed = False

    def enroll(self, *, physical_usb_confirmed: bool, owner_approved: bool, controller_claim: str):
        if not physical_usb_confirmed or not owner_approved or not controller_claim:
            return False
        self.disconnect()
        self.enrollment_generation += 1
        self.enrolled_claim = controller_claim
        self.revoked = False
        self.risk_approved = False
        self.descriptor_allowed = False
        self.phase = Phase.ENROLLED
        return True

    def authorize_risk(self, approved: bool):
        # Not a radio-authentication claim. Production use needs separate Owner consent.
        self.risk_approved = bool(approved) and not self.revoked
        if not self.risk_approved:
            self.disconnect()

    def revoke(self):
        self.disconnect()
        self.enrollment_generation += 1
        self.revoked = True
        self.risk_approved = False
        self.enrolled_claim = None
        self.phase = Phase.UNENROLLED

    def adapter_changed(self):
        self.adapter_generation += 1
        self.revoke()

    def disconnect(self):
        self.epoch += 1
        self.descriptor_allowed = False
        self.phase = Phase.UNENROLLED if self.revoked else Phase.ENROLLED

    def connect(self, *, radio_claim: str, transport: str = "BR_EDR"):
        # A matching address/claim is spoofable. This is intentionally bounded risk.
        if (self.revoked or not self.risk_approved or self.phase != Phase.ENROLLED
                or transport != "BR_EDR" or not radio_claim
                or radio_claim != self.enrolled_claim):
            return None
        self.epoch += 1
        self.phase = Phase.ACL
        return Event(self.epoch, self.enrollment_generation, self.adapter_generation)

    def _valid(self, event):
        return (isinstance(event, Event) and not self.revoked and self.risk_approved
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

    def allow_descriptor(self, event, *, validated_gamepad_only: bool):
        # Test predicate, NOT a real HID descriptor parser. Must precede UHID_CREATE.
        if not self._valid(event) or self.phase != Phase.BOTH_CHANNELS or not validated_gamepad_only:
            return False
        self.descriptor_allowed = True
        return True

    def java_admit(self, event, *, quiet: bool = False, forbidden: bool = False):
        if (not self._valid(event) or self.phase != Phase.BOTH_CHANNELS
                or not self.descriptor_allowed or quiet or forbidden):
            return False
        self.phase = Phase.JAVA
        return True

    def uhid_ready(self, event, *, report_completion_verified: bool):
        if not self._valid(event) or self.phase != Phase.JAVA or not report_completion_verified:
            return False
        self.phase = Phase.ACTIVE
        return True

    def input_report(self, event, *, validated_report: bool):
        # Test predicate, NOT a parser; only a future kernel-bound report gate.
        return self._valid(event) and self.phase == Phase.ACTIVE and validated_report
