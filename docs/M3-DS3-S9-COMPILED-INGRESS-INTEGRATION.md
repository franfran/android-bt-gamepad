# S9 cross-file extracted source compile verification

Added `experiments/m3-source-first/test_compiled_s9_integration.py` to verify the existing S9 3-file transformation beyond `git apply`.

The test fetches pinned upstream H618 Android12 BTIF source, invokes `test_integrated_btif_allocation_source.transform`, extracts **the real transformed** `btif_hh_try_enqueue_setreport` and `btif_hh_setreport` definitions plus the changed `UHID_SET_REPORT` ingress block, and compiles/runs that combined C++ with GCC and Clang under strict warnings. It checks buffer allocation rejection, successful queue attempt, supported report type, unsupported report type and original legacy wrapper. Header source is also checked for the declaration.

First CI failure was in synthetic test stubs: missing `NULL` include, wrong representation of `ev.u.set_report`, and unused warning due to logging stub. Second failure was a literal `\\n` in generated include. Corrections are in commits `bd49ce69`, `6691e8d2`, `599506c9`.

**Scope:** This is an extracted-source host compilation with mocked Android types and BTA dispatch, **not** compilation of the complete three real translation units, Android12 Soong, ARM32, OEM ABI, or a functioning UHID completion path. `queued_locally` remains local acceptance only and the request ID is logged on failure; no kernel reply is written.

No M3 operations, no Bluetooth security changes, no merge. PR #51 stays Draft and PR #50 remains independent.
