"""Pure offline cable-enrollment decision model. NOT an Android patch.

A passing decision here is not proof of cryptographic identity, live Bluetooth
compatibility, or safe native injection.
"""
from dataclasses import dataclass

HID_PSMS = frozenset((0x11, 0x13))

@dataclass(frozen=True)
class Enrollment:
    controller_token: str
    host_token: str
    physical_usb_verified: bool
    owner_approved: bool
    revoked: bool = False

@dataclass(frozen=True)
class Candidate:
    controller_token: str
    host_token: str
    psm: int
    profile: str
    native_hook_verified: bool
    hid_hook_verified: bool
    duplicate: bool = False

def classify(enrollment: Enrollment | None, req: Candidate) -> str:
    # Tokens deliberately represent local opaque identities, not real MACs.
    if enrollment is None or not enrollment.physical_usb_verified:
        return "DENY_NO_USB_ENROLLMENT"
    if not enrollment.owner_approved or enrollment.revoked:
        return "DENY_NOT_AUTHORIZED"
    if req.controller_token != enrollment.controller_token:
        return "DENY_CONTROLLER_MISMATCH"
    if req.host_token != enrollment.host_token:
        return "DENY_HOST_MISMATCH"
    if req.psm not in HID_PSMS or req.profile != "HID_HOST":
        return "DENY_NOT_DS3_HID_PATH"
    if req.duplicate:
        return "DENY_DUPLICATE"
    if not req.native_hook_verified or not req.hid_hook_verified:
        return "DENY_MISSING_TWO_GATE_INTEGRATION"
    return "CANDIDATE_ONLY_NOT_AUTHENTICATED"
