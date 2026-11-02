"""Offline model ONLY: immutable per-session descriptor events, not an Android API."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Ticket:
    handle: int
    epoch: int


@dataclass
class Candidate:
    native_allowed: bool
    descriptor: bytes | None = None
    java_allowed: bool = False
    created: bool = False


class DescriptorEnvelopeGate:
    def __init__(self):
        self._epoch = 0
        self._sessions: dict[int, tuple[Ticket, Candidate]] = {}
        self.current_device_handle = None  # Legacy shared-pointer hazard demo only.

    def opened(self, handle: int, *, native_allowed: bool) -> Ticket:
        self._epoch += 1
        ticket = Ticket(handle, self._epoch)
        self._sessions[handle] = (ticket, Candidate(native_allowed))
        self.current_device_handle = handle
        return ticket

    def _candidate(self, ticket: Ticket) -> Candidate | None:
        pair = self._sessions.get(ticket.handle)
        return pair[1] if pair is not None and pair[0] == ticket else None

    def accept_descriptor(self, ticket: Ticket, payload: bytes | bytearray,
                          *, descriptor_valid: bool) -> bool:
        candidate = self._candidate(ticket)
        if (candidate is None or not candidate.native_allowed or not descriptor_valid
                or not payload or candidate.descriptor is not None or candidate.created):
            return False
        candidate.descriptor = bytes(payload)  # Snapshot; no deferred borrowed pointer.
        return True

    def java_decision(self, ticket: Ticket, *, allowed: bool) -> bool:
        candidate = self._candidate(ticket)
        if candidate is None or not candidate.native_allowed:
            return False
        if not allowed:
            self.disconnect(ticket)
            return False
        candidate.java_allowed = True
        return True

    def release_uhid_create(self, ticket: Ticket) -> bytes | None:
        candidate = self._candidate(ticket)
        if (candidate is None or not candidate.native_allowed or not candidate.java_allowed
                or candidate.descriptor is None or candidate.created):
            return None
        candidate.created = True
        return candidate.descriptor

    def disconnect(self, ticket: Ticket) -> bool:
        if self._candidate(ticket) is None:
            return False
        self._sessions.pop(ticket.handle)
        return True

    def legacy_unbound_target(self) -> int | None:
        """Illustrates selection by a mutable global, NOT an actual exploit test."""
        return self.current_device_handle
