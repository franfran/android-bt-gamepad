# S7 pre-send producer-origin ownership — host-only implementation

**Context:** S6 confirms that `UHID_SET_REPORT`, `UHID_OUTPUT` Feature and Java HAL report operations converge on BTA's SET path. A request-ID-only FIFO would allow cross-producer attribution.

**This milestone:** `experiments/m3-source-first/ingress_origin_owner.h` implements an offline C++17 ownership contract recording `IngressOrigin`, original kernel request ID (kernel SET only), and session generation **before** a hypothetical shared send. A competing source is rejected; only the matching generation may consume a local failure. Every consumed transaction permanently quarantines that handle because a later untagged remote handshake still cannot be safely attributed. The test exercises kernel, output and HAL contention, nonkernel ID rejection, wrong generation, exactly-once failure, disconnect and handle isolation.

This is **not wired into actual Fluoride** and contains no UHID event, BTA message changes or device operations. It is deliberately too restrictive to support continuous DS3 input. A production integration must identify origin at real entry points, correctly route pre-BTA allocation errors, preserve shared message lifetimes and prove remote-handshake/session identity before any kernel reply.

Current experimental BTA admission guard remains globally scoped and deployment NO_GO. ARM32 Soong, OEM binary ABI, authentication `0x22`, and Java bond policy are independent open gates. PR #51 stays Draft, PR #50 unmerged.
