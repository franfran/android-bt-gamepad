#include "ds3_policy.h"
#include <string.h>

ds3_policy_result ds3_policy_evaluate(const ds3_enrollment *enrolled,
                                      const ds3_security_request *req) {
    if (!enrolled || !req) return DS3_POLICY_NO_CHANGE;
    if (!enrolled->usb_enrolled || !enrolled->confirmed_ds3_identity)
        return DS3_POLICY_NO_CHANGE;
    if (memcmp(enrolled->addr, req->remote_addr, sizeof(enrolled->addr)) != 0)
        return DS3_POLICY_NO_CHANGE;
    if (!req->incoming) return DS3_POLICY_NO_CHANGE;
    if (req->psm != DS3_HID_CONTROL_PSM &&
        req->psm != DS3_HID_INTERRUPT_PSM) return DS3_POLICY_NO_CHANGE;
    /* Only annotate the observed standard HID mask; fail closed otherwise. */
    if (req->original_security_mask != (BTM_SEC_IN_AUTHENTICATE |
            BTM_SEC_IN_ENCRYPT | BTM_SEC_OUT_AUTHENTICATE |
            BTM_SEC_OUT_ENCRYPT)) return DS3_POLICY_NO_CHANGE;
    return DS3_POLICY_COMPAT_CANDIDATE;
}
