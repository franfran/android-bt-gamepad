"""Offline SET_REPORT transaction contract, NOT a native hook.

The M3 callback has neither UHID ID nor generation. One-in-flight per
device is NECESSARY but INSUFFICIENT to prove reply attribution: this
model assumes external native evidence that completion is strictly ordered
and callbacks cannot be stale at any newly submitted request.

Once timeout/disconnect occurs, this manager never permits reuse of that
device key. A new manager requires independently verified isolation of the
old callback source (e.g. confirmed old process terminated), outside here.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Completion:
    device: str
    request_id: int
    native_status: int

@dataclass(frozen=True)
class Pending:
    request_id: int
    deadline: int

class SetReportTransactions:
    def __init__(self):
        self._pending: dict[str, Pending] = {}
        self._poisoned: set[str] = set()

    def submit(self, device: str, request_id: int, *, now: int, timeout: int) -> bool:
        if not device or not isinstance(request_id, int) or isinstance(request_id, bool):
            return False
        if not isinstance(now, int) or isinstance(now, bool):
            return False
        if not isinstance(timeout, int) or isinstance(timeout, bool):
            return False
        if not (0 <= request_id <= 0xffffffff) or timeout <= 0:
            return False
        if device in self._poisoned or device in self._pending:
            return False
        self._pending[device] = Pending(request_id, now + timeout)
        return True

    def complete(self, device: str, *, native_status: int, now: int) -> Completion | None:
        p = self._pending.get(device)
        if p is None or device in self._poisoned:
            return None
        if now >= p.deadline:
            self._pending.pop(device)
            self._poisoned.add(device)
            return None
        self._pending.pop(device)
        return Completion(device, p.request_id, native_status)

    def expire(self, device: str, *, now: int) -> bool:
        p = self._pending.get(device)
        if p is None or now < p.deadline:
            return False
        self._pending.pop(device)
        self._poisoned.add(device)
        return True

    def disconnect(self, device: str) -> None:
        self._pending.pop(device, None)
        self._poisoned.add(device)

    def quarantined(self, device: str) -> bool:
        return device in self._poisoned
