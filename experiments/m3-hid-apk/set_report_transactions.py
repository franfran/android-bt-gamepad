"""Offline SET_REPORT transaction contract; NOT a native hook or deployment code.

M3 completion callback has no request ID: permit one in-flight SET per device.
Timeout/disconnect quarantines the device so stale callbacks cannot be
misattributed to later requests. Completion carries raw native status only;
status->UHID errno mapping must be separately verified, never fabricated.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Completion:
    device: str
    request_id: int
    native_status: int

@dataclass
class Pending:
    request_id: int
    deadline: int

class SetReportTransactions:
    def __init__(self):
        self._pending: dict[str, Pending] = {}
        self._poisoned: set[str] = set()

    def submit(self, device: str, request_id: int, *, now: int, timeout: int) -> bool:
        if not device or not (0 <= request_id <= 0xffffffff) or timeout <= 0:
            return False
        if device in self._poisoned or device in self._pending:
            return False
        self._pending[device] = Pending(request_id, now + timeout)
        return True

    def complete(self, device: str, *, native_status: int, now: int) -> Completion | None:
        pending = self._pending.get(device)
        if pending is None or device in self._poisoned:
            return None
        if now >= pending.deadline:
            self._pending.pop(device)
            self._poisoned.add(device)
            return None
        self._pending.pop(device)
        return Completion(device, pending.request_id, native_status)

    def expire(self, device: str, *, now: int) -> bool:
        pending = self._pending.get(device)
        if pending is None or now < pending.deadline:
            return False
        self._pending.pop(device)
        self._poisoned.add(device)
        return True

    def disconnect(self, device: str) -> None:
        self._pending.pop(device, None)
        self._poisoned.add(device)

    def reset_after_verified_new_session(self, device: str) -> bool:
        # Only call after external proof all callbacks from old session drained.
        # This class CANNOT establish that proof; no automatic reset is allowed.
        if device in self._pending:
            return False
        self._poisoned.discard(device)
        return True
