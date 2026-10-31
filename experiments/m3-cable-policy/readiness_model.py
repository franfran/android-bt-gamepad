"""Offline readiness tracking; does not bypass or emulate Bluetooth authentication.

Candidate PSM detection != L2CAP configuration != HID Host admission !=
Android InputDevice. Never use this model to grant wireless access.
"""
from dataclasses import dataclass, field
CONTROL, INTERRUPT = 0x11, 0x13

@dataclass
class Readiness:
    candidate_psms: set[int] = field(default_factory=set)
    configured_psms: set[int] = field(default_factory=set)
    native_connected: bool = False
    java_admitted: bool = False
    input_device_ready: bool = False
    closed: bool = False

    def candidate(self, psm: int) -> bool:
        if self.closed or psm not in (CONTROL, INTERRUPT): return False
        if psm == INTERRUPT and CONTROL not in self.candidate_psms: return False
        if psm in self.candidate_psms: return False
        self.candidate_psms.add(psm)
        return True

    def configured(self, psm: int) -> bool:
        if self.closed or psm not in self.candidate_psms: return False
        self.configured_psms.add(psm)
        return True

    def native_connection(self) -> bool:
        if self.closed or self.configured_psms != {CONTROL, INTERRUPT}: return False
        self.native_connected = True
        return True

    def java_admission(self) -> bool:
        if self.closed or not self.native_connected: return False
        self.java_admitted = True
        return True

    def input_ready(self) -> bool:
        if self.closed or not self.java_admitted: return False
        self.input_device_ready = True
        return True

    def operational(self) -> bool:
        return not self.closed and self.input_device_ready

    def reset(self) -> None:
        self.candidate_psms.clear()
        self.configured_psms.clear()
        self.native_connected = False
        self.java_admitted = False
        self.input_device_ready = False
        self.closed = False

    def disconnect(self) -> None:
        self.reset()
        self.closed = True
