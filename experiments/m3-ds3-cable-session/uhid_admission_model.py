"""Offline model of a STRICT, proposed per-session pre-UHID admission barrier.

NOT production Bluetooth, HID parsing, real radio authentication, or an Android API.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Ticket:
    handle: int
    epoch: int


@dataclass
class Candidate:
    native_ok: bool
    descriptor_ok: bool = False
    java_ok: bool = False
    created: bool = False
    kernel_ready: bool = False


class AdmissionGate:
    def __init__(self):
        self.epoch = 0
        self.sessions = {}

    def opened(self, handle, *, native_ok):
        self.epoch += 1
        ticket = Ticket(handle, self.epoch)
        self.sessions[handle] = (ticket, Candidate(native_ok))
        return ticket

    def _current(self, ticket):
        pair = self.sessions.get(ticket.handle)
        return pair[1] if pair and pair[0] == ticket else None

    def descriptor_event(self, ticket, *, validated_gamepad):
        candidate = self._current(ticket)
        if candidate is None or not candidate.native_ok or not validated_gamepad:
            return False
        candidate.descriptor_ok = True
        return True

    def java_decision(self, ticket, *, permitted):
        candidate = self._current(ticket)
        if candidate is None:
            return False
        if not permitted:
            self.close(ticket)
            return False
        if not candidate.native_ok:
            return False
        candidate.java_ok = True
        return True

    def can_create(self, ticket):
        candidate = self._current(ticket)
        return bool(candidate and candidate.native_ok and candidate.descriptor_ok
                    and candidate.java_ok and not candidate.created)

    def uhid_create(self, ticket):
        if not self.can_create(ticket):
            return False
        self._current(ticket).created = True
        return True

    def kernel_ready(self, ticket, ready):
        candidate = self._current(ticket)
        if candidate is None or not candidate.created:
            return False
        candidate.kernel_ready = bool(ready)
        return True

    def uhid_input(self, ticket, *, validated_report):
        candidate = self._current(ticket)
        return bool(candidate and candidate.native_ok and candidate.descriptor_ok
                    and candidate.java_ok and candidate.created and candidate.kernel_ready
                    and validated_report)

    def close(self, ticket):
        if self._current(ticket) is None:
            return False
        del self.sessions[ticket.handle]
        return True
