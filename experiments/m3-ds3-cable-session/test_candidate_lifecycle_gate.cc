#include "candidate_lifecycle_gate.h"
#include <atomic>
#include <future>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>
using retrobox::CandidateLifecycleGate;
using retrobox::CandidateLifecycleTicket;
using retrobox::UhidEventKind;
static void Check(bool b) { if (!b) throw std::runtime_error("lifecycle invariant"); }
int main() {
  int n = 0;
  auto check = [&](bool b) { Check(b); ++n; };
  CandidateLifecycleGate gate;
  CandidateLifecycleTicket a{14, 4, 101, 1};
  int writes = 0;
  auto write = [&] { ++writes; return 0; };
  check(gate.WithKernelWrite(14,UhidEventKind::kCreate,write)==0);
  check(writes == 1); // ordinary HID unchanged
  check(gate.RegisterCandidate(a));
  check(gate.IsBlocked(14));
  check(gate.WithKernelWrite(14,UhidEventKind::kCreate,write)==-EACCES);
  check(gate.WithKernelWrite(14,UhidEventKind::kInput,write)==-EACCES);
  check(writes == 1); // candidate never entered kernel
  check(gate.WithKernelWrite(14,UhidEventKind::kDestroy,write)==0);
  check(writes == 2); // still permits destroy
  check(gate.WithKernelWrite(15,UhidEventKind::kInput,write)==0);
  check(writes == 3); // separate device unchanged
  check(!gate.RegisterCandidate(a));
  check(!gate.RegisterCandidate({14,5,200,3}));
  check(!gate.RegisterCandidate({15,4,200,3}));
  check(!gate.Quarantine({14,4,99,1}));
  check(gate.Quarantine(a));
  check(!gate.Quarantine(a));
  check(gate.IsBlocked(14)); // disconnect does NOT unblock fd
  check(gate.WithKernelWrite(14,UhidEventKind::kInput,write)==-EACCES);
  int close_count=0;
  auto close_fail = [&](int){ ++close_count; return false; };
  auto close_ok = [&](int fd){ ++close_count; return fd==14; };
  check(!gate.CloseQuarantined({14,4,101,2},close_ok));
  check(close_count==0); // stale token never invokes close
  check(!gate.CloseQuarantined(a,close_fail));
  check(gate.IsBlocked(14));
  check(gate.CloseQuarantined(a,close_ok));
  check(!gate.IsBlocked(14));
  check(close_count==2);
  check(!gate.CloseQuarantined(a,close_ok));
  check(gate.RegisterCandidate({14,4,102,2}));
  check(!gate.Quarantine(a)); // old disconnect not matched
  check(gate.IsBlocked(14));
  check(gate.Quarantine({14,4,102,2}));
  check(gate.CloseQuarantined({14,4,102,2},close_ok));
  check(!gate.RegisterCandidate({-1,4,1,1}));
  check(!gate.RegisterCandidate({14,0xff,1,1}));
  check(!gate.RegisterCandidate({14,4,0,1}));
  check(!gate.RegisterCandidate({14,4,1,0}));
  std::vector<CandidateLifecycleTicket> tickets;
  for(int i=0;i<8;++i){CandidateLifecycleTicket t{100+i,static_cast<uint8_t>(i),33,static_cast<uint64_t>(i+1)};check(gate.RegisterCandidate(t));tickets.push_back(t);}
  check(gate.Held()==8);
  check(!gate.RegisterCandidate({250, 80, 1, 1})); // caller must abort
  for(const auto& t:tickets) check(gate.IsBlocked(t.fd));
  for(const auto& t:tickets){check(gate.Quarantine(t));check(gate.CloseQuarantined(t,[](int){return true;}));}
  check(gate.Held()==0);
  // Hold lock while write runs; an interleaved candidate register must not
  // be accepted until the previously unclassified writer has finished.
  std::promise<void> in_write, continue_write;
  auto started=in_write.get_future(); auto released=continue_write.get_future();
  std::atomic<bool> registration_finished{false};
  std::thread writer([&]{
    gate.WithKernelWrite(71,UhidEventKind::kInput,[&]{in_write.set_value();released.wait();return 0;});
  });
  started.wait();
  std::thread registerer([&]{
    if(!gate.RegisterCandidate({71,7,987,5}))std::terminate();
    registration_finished=true;
  });
  // Cannot force the registerer to be scheduled here; post-join result proves
  // final state, not scheduler interleaving timing.
  continue_write.set_value();
  writer.join(); registerer.join();
  check(registration_finished);
  check(gate.IsBlocked(71));
  check(gate.WithKernelWrite(71,UhidEventKind::kInput,write)==-EACCES);
  check(gate.Quarantine({71,7,987,5}));
  check(gate.CloseQuarantined({71,7,987,5},[](int){return true;}));
  std::cout << n << "/" << n << " PASS (candidate lifecycle quarantine + atomic writer host)\n";
}
