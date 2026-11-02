#include "candidate_uhid_fence.h"
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>

using retrobox::CandidateUhidFence;
using retrobox::FenceTicket;
static void Check(bool value) { if (!value) throw std::runtime_error("fence assertion"); }

int main() {
  int cases = 0;
  auto test = [&](bool result) { Check(result); ++cases; };
  CandidateUhidFence fence;
  const FenceTicket a{14, 4, 101, 1};
  test(fence.AllowKernelEvent(14, true));  // unclassified stock path
  test(fence.RegisterCandidate(a));
  test(!fence.AllowKernelEvent(14, true)); // UHID_CREATE
  test(!fence.AllowKernelEvent(14, true)); // UHID_INPUT same fence
  test(fence.AllowKernelEvent(14, false)); // unrelated UHID event
  test(fence.AllowKernelEvent(15, true));  // other device unchanged
  test(!fence.RegisterCandidate(a));
  test(!fence.RegisterCandidate({14, 5, 102, 2})); // same fd reused
  test(!fence.RegisterCandidate({15, 4, 102, 2})); // same handle
  test(fence.Pending() == 1);
  test(!fence.Revoke({14, 4, 100, 1})); // stale ACL
  test(!fence.Revoke({14, 4, 101, 2})); // stale request
  test(!fence.AllowKernelEvent(14, true));
  test(fence.Revoke(a));
  test(fence.AllowKernelEvent(14, true));
  test(!fence.Revoke(a));
  test(fence.RegisterCandidate({14, 4, 102, 2}));
  test(!fence.Revoke(a));
  test(!fence.AllowKernelEvent(14, true));
  test(fence.Revoke({14, 4, 102, 2}));
  test(!fence.RegisterCandidate({-1, 4, 101, 1}));
  test(!fence.RegisterCandidate({14, 0xff, 101, 1}));
  test(!fence.RegisterCandidate({14, 4, 0, 1}));
  test(!fence.RegisterCandidate({14, 4, 101, 0}));
  std::vector<FenceTicket> all;
  for (int i = 0; i < 8; ++i) {
    FenceTicket t{100 + i, static_cast<uint8_t>(i), 123, static_cast<uint64_t>(i+1)};
    test(fence.RegisterCandidate(t));
    all.push_back(t);
  }
  test(fence.Pending() == 8);
  test(!fence.RegisterCandidate({200, 40, 123, 10}));
  for (auto t : all) test(!fence.AllowKernelEvent(t.fd, true));
  for (auto t : all) test(fence.Revoke(t));
  test(fence.Pending() == 0);
  // Parallel reads cannot race against the protected map.
  FenceTicket in_flight{71, 7, 99, 8};
  test(fence.RegisterCandidate(in_flight));
  std::thread reader([&] {
    for (int i = 0; i < 1000; ++i)
      if (fence.AllowKernelEvent(71, true))
        std::terminate(); // remains blocked until thread joins
  });
  reader.join();
  test(fence.Revoke(in_flight));
  std::cout << cases << "/" << cases
            << " PASS (candidate-only UHID fence host model)\n";
}
