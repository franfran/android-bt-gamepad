#include "transaction_owner.h"
#include <cassert>
#include <iostream>
int main() {
  using O = Origin; using C = CompletionKind;
  TransactionOwner x;
  assert(x.begin(1, O::KernelUhidSet, 123, 10, 5));
  assert(!x.begin(1, O::UhidOutputFeature, 0, 11, 5));
  assert(!x.begin(1, O::JavaHalSet, 0, 11, 5));
  assert(!x.begin(1, O::GetReport, 0, 11, 5));
  auto ok = x.finish(1, 0, 12, C::Handshake);
  assert(ok && ok->origin == O::KernelUhidSet && ok->kernel_id == 123);
  assert(!x.finish(1, 0, 13, C::Handshake));
  assert(!x.begin(1, O::KernelUhidSet, 124, 14, 5));
  assert(x.begin(2, O::UhidOutputFeature, 0, 0, 8));
  auto out = x.finish(2, 7, 2, C::Handshake);
  assert(out && out->origin != O::KernelUhidSet && out->kernel_id == 0);
  assert(x.begin(3, O::JavaHalSet, 0, 0, 10));
  auto fail = x.finish(3, 1, 1, C::LocalSendFailure);
  assert(fail && fail->native_status == 1 && fail->kind == C::LocalSendFailure);
  assert(x.begin(4, O::KernelUhidSet, 77, 0, 5));
  assert(!x.expire(4, 4) && x.expire(4, 5));
  assert(!x.finish(4, 0, 6, C::Handshake));
  assert(x.begin(5, O::KernelUhidSet, 88, 0, 5));
  assert(!x.finish(5, 0, 5, C::Handshake));
  assert(x.phase(5) == Phase::Quarantined);
  assert(x.begin(6, O::KernelUhidSet, 99, 0, 10));
  x.disconnect(6);
  assert(!x.finish(6, 0, 1, C::Handshake));
  assert(!x.begin(6, O::KernelUhidSet, 100, 2, 10));
  assert(x.begin(7, O::GetReport, 0, 0, 5));
  assert(!x.begin(8, O::GetReport, 10, 0, 5));
  assert(!x.begin(8, O::KernelUhidSet, 10, 0, 0));
  assert(!x.begin(8, O::KernelUhidSet, 10, UINT64_MAX, 1));
  assert(x.begin(8, O::KernelUhidSet, UINT32_MAX, 0, 1));
  std::cout << "transaction ownership host assertions PASS\n";
}
