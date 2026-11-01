# S11 Verify real modified source ownership in Soong

At public BPI H618 Android12 commit `250eabfc529518b7f26432663ed0a867ab2f625d`, the actual `system/bt/btif/Android.bp` `cc_library_static { name: "libbtif" }` lists **both** `co/bta_hh_co.cc` and `src/btif_hh.cc` as source translation units. `system/bt/main/Android.bp` `cc_library_shared { name: "libbluetooth" }` includes `libbtif` in `whole_static_libs`. The new S9 header declaration would be in `btif/include/btif_hh.h` used by these files.

`experiments/m3-source-first/test_pinned_btif_build_membership.py` performs source-pinned checks of this exact Soong path on each host CI run; it also asserts the upstream header does not already include the experimental API.

**This resolves the question of module membership, not build feasibility itself.** Successful host or ARM bare-metal source-fragment compilation does not prove full Android12 Soong build, linker-namespace compatibility, 32-bit ABI compatibility with original M3 `libbluetooth.so`, kernel reply transaction ownership or DS3 authentication.

Next actionable work is full pinned Android BSP checkout, correct device target selection, build output evidence and offline symbol/DT_NEEDED comparison. Do not deploy, replace system library, or weaken systemwide Bluetooth policy. PR #51 remains Draft, PR #50 separate.
