// Offline proof of a source-level BTA w4_evt overwrite hazard.
// This is NOT an M3 patch, and does not claim that this interleaving occurred on hardware.
#include <cassert>
#include <cstdint>
#include <iostream>

enum class Op : uint8_t { None = 0, KernelSet = 5, HalGet = 4, HalSet = 6 };
struct LegacyBta {
  Op w4_evt = Op::None;
  void successful_send(Op event) { w4_evt = event; }  // mirrors assignment in bta_hh_write_dev_act
  Op handshake() { auto result = w4_evt; w4_evt = Op::None; return result; }
};
struct GuardedBta {
  Op w4_evt = Op::None;
  bool submit(Op event, bool successful_write) {
    // Offline conceptual requirement: guard BEFORE write, not after.
    if (event == Op::None || w4_evt != Op::None) return false;
    if (!successful_write) return false;
    w4_evt = event;
    return true;
  }
  Op handshake() { auto result = w4_evt; w4_evt = Op::None; return result; }
};
int main() {
  LegacyBta legacy;
  legacy.successful_send(Op::KernelSet);
  legacy.successful_send(Op::HalGet);
  assert(legacy.handshake() == Op::HalGet); // First kernel request lost its event tag.
  assert(legacy.handshake() == Op::None);
  GuardedBta guarded;
  assert(guarded.submit(Op::KernelSet, true));
  assert(!guarded.submit(Op::HalGet, true));
  assert(guarded.handshake() == Op::KernelSet);
  assert(guarded.submit(Op::HalGet, true));
  assert(guarded.handshake() == Op::HalGet);
  assert(!guarded.submit(Op::HalSet, false));
  assert(guarded.submit(Op::HalSet, true));
  std::cout << "BTA w4_evt overwrite reproduction and guard model PASS\n";
}
