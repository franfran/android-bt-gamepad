# S16 — BSP output provenance and incremental build safety

The Android BSP build wrapper now rejects an incorrectly labelled `baseline` run when any of the three S9 BTIF files is dirty; it likewise rejects `s9` if none of the three files is dirty. Every run captures the three-file source diff and pinned BSP HEAD for later attribution. The wrapper checks the real `system/lib/libbluetooth.so` ELF32 ARM artifact after invoking Soong. The script warns when that file predates the build invocation rather than treating it as failure: **successful incremental Soong builds legitimately reuse prior artifacts**. The build log, source diff and ELF content must all be inspected together.

No full Android BSP build ran in the current environment. Upstream oversized source files and a genuine Linux Soong host remain the build blocker. `apollo_p1-userdebug` remains an independently verified candidate, not OEM-equivalence proof. The S9 integration is still only local enqueue reporting, not valid remote HID acknowledgement.

Evidence cannot imply DS3 wireless connectivity; native authentication, Java bond policy and kernel SET_REPORT ownership are unresolved. No M3 changes, merges, firmware flashing or deployment.
