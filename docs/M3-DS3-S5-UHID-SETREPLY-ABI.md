# S5 Linux 5.4 UHID SET_REPORT_REPLY ABI and identity contract

**2026-11-01 · host-only source review.** Upstream Linux `v5.4`:
- `include/uapi/linux/uhid.h`: enum `UHID_SET_REPORT_REPLY` and packed `struct uhid_set_report_reply_req { __u32 id; __u16 err; }`. **6-byte packed body**. Event container is a different structure; do not directly send a 6-byte body to /dev/uhid.
- `drivers/hid/uhid.c`: `__uhid_report_queue_and_wait` assigns a 32-bit ID; `uhid_report_wake_up` checks matching event type and request ID. `uhid_hid_set_report` tests `set_report_reply.err` as zero/nonzero: nonzero produces `-EIO`, zero returns report byte count. Do NOT copy a raw BTA enum or negative Linux errno into this field.
- `UHID_SET_REPORT_REPLY` event value 14 in this ABI; *not* BTA internal message `0x000e`. Never mix event class with transaction identity.

Code: `experiments/m3-source-first/test_uhid_set_reply_contract.cc`. Host-only fixture checks 32-bit request IDs, 6-byte packed response body, boolean success/failure, origin isolation, generation mismatch, missing completion and unproven callback identity. Test constructs a reply **body**, does not write a `struct uhid_event` or interact with the kernel.

**Warning:** Model parameter `attribution_proven` is a synthetic test input and is **not** established by M3 Fluoride. Real source `bta_hh_co_set_rpt_rsp` has only handle/status. Consequently the production UHID writer remains prohibited until ownership is proven.

Additional missing evidence: actual M3 downstream `uhid.h` and kernel implementation comparison, exact error/status classes, lifecycle on disconnect, complete Soong/ARM32 compiled artifact and vendor JNI ABI. These are independent of DS3 cable-enrolled native authentication and Java HID Host bond policy. Status = **NO_GO** for live deployment, library patch, flashing, injection or merge.
