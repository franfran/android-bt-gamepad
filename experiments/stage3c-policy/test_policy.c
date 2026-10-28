#include "ds3_policy.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    ds3_enrollment e = {{0x00,0x06,0xf7,0xb7,0xe1,0x81}, true, true};
    ds3_security_request r = {{0x00,0x06,0xf7,0xb7,0xe1,0x81}, 0x11, true, 0x36};
    unsigned n = 0;
#define CHECK(expected) do { assert(ds3_policy_evaluate(&e,&r)==(expected)); ++n; } while(0)
    CHECK(DS3_POLICY_COMPAT_CANDIDATE);
    r.psm=0x13; CHECK(DS3_POLICY_COMPAT_CANDIDATE);
    r.psm=0x01; CHECK(DS3_POLICY_NO_CHANGE);
    r.psm=0x11; r.incoming=false; CHECK(DS3_POLICY_NO_CHANGE);
    r.incoming=true; r.original_security_mask=0x00; CHECK(DS3_POLICY_NO_CHANGE);
    r.original_security_mask=0x36; r.remote_addr[5] ^= 1; CHECK(DS3_POLICY_NO_CHANGE);
    r.remote_addr[5] ^= 1; e.usb_enrolled=false; CHECK(DS3_POLICY_NO_CHANGE);
    e.usb_enrolled=true; e.confirmed_ds3_identity=false; CHECK(DS3_POLICY_NO_CHANGE);
    e.confirmed_ds3_identity=true;
    assert(ds3_policy_evaluate(NULL,&r)==DS3_POLICY_NO_CHANGE); ++n;
    assert(ds3_policy_evaluate(&e,NULL)==DS3_POLICY_NO_CHANGE); ++n;
    puts("PASS: 10 policy cases (candidate only; no Bluetooth security bypass)");
    return 0;
}
