#ifndef RETROBOX_DS3_POLICY_H
#define RETROBOX_DS3_POLICY_H
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

/* Standalone test model. No modification to system Bluetooth stack. */
#define DS3_HID_CONTROL_PSM 0x0011u
#define DS3_HID_INTERRUPT_PSM 0x0013u
#define BTM_SEC_IN_AUTHENTICATE 0x0002u
#define BTM_SEC_IN_ENCRYPT 0x0004u
#define BTM_SEC_OUT_AUTHENTICATE 0x0010u
#define BTM_SEC_OUT_ENCRYPT 0x0020u

typedef struct {
    uint8_t addr[6];
    bool usb_enrolled;
    bool confirmed_ds3_identity; /* must come from trusted USB enrollment */
} ds3_enrollment;

typedef struct {
    uint8_t remote_addr[6];
    uint16_t psm;
    bool incoming;
    uint16_t original_security_mask;
} ds3_security_request;

typedef enum {
    DS3_POLICY_NO_CHANGE = 0,
    DS3_POLICY_COMPAT_CANDIDATE = 1
} ds3_policy_result;

/* This returns a candidate; it DOES NOT authorize an actual Bluetooth connection. */
ds3_policy_result ds3_policy_evaluate(const ds3_enrollment *enrolled,
                                      const ds3_security_request *req);
#endif
