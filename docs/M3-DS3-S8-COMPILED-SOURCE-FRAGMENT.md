# S8 compiled patched BTIF source fragment

New `test_compiled_btif_patch.py` retrieves the immutable public BSP `btif/src/btif_hh.cc` at `250eabfc529518b7f26432663ed0a867ab2f625d`, checks the Git blob hash `9e5db0c1af234881048732d8bc4816f23b2a33ba`, applies `btif_allocation_boundary_EXPERIMENTAL.patch`, then extracts the **actual patched function definitions** (the private bool helper and original public void wrapper).

It injects *host stubs* for dependencies and compiles/runs the extracted code with GCC and Clang, `-std=c++17 -Wall -Wextra -Werror -pedantic`. It checks that failed buffer allocation doesn't enqueue and that successful allocation invokes BTA exactly once, including wrapper behavior.

This is stronger than mere `git apply`, but is NOT complete Android source compile, Soong/ARM32 build, toolchain/ABI matching, true Bluetooth execution, or a source-safe integration approval. The test deliberately mocks BTA, `BT_HDR`, and Android headers. A fully integrated build and request identity propagation remain pending. All experimental patches remain **deployment NO_GO**.
