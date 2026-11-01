// Offline-only scheduler design experiment. NOT Fluoride or a deployable patch.
#include <cassert>
#include <cstdint>
#include <deque>
#include <iostream>
#include <map>
#include <optional>
enum class Source { Kernel, UhidOutput, Hal };
struct Job { Source source; uint32_t kernel_id; };
struct Slot { std::optional<Job> active; std::deque<Job> waiting; bool poisoned=false; };
class Scheduler {
 public:
  bool enqueue(int handle, Job job) {
    Slot& s=slots_[handle];
    if (s.poisoned || s.waiting.size() >= 3 || (job.source!=Source::Kernel && job.kernel_id!=0)) return false;
    // Only one command is ever issued; queue stays blocked until proof of epoch isolation.
    if (!s.active) s.active=job;
    else s.waiting.push_back(job);
    return true;
  }
  bool has_active(int h) const {
    auto it=slots_.find(h); return it!=slots_.end() && it->second.active.has_value();
  }
  size_t waiting(int h) const { auto it=slots_.find(h);return it==slots_.end()?0:it->second.waiting.size(); }
  bool finish(int h) {
    auto it=slots_.find(h);
    if (it==slots_.end() || !it->second.active || it->second.poisoned) return false;
    // No auto-promotion: untagged stale callback may match the queued next transaction.
    poison(it->second);
    return true;
  }
  void timeout_or_disconnect(int h) { poison(slots_[h]); }
  bool poisoned(int h) const {
    auto it=slots_.find(h);return it!=slots_.end() && it->second.poisoned;
  }
 private:
  static void poison(Slot& s) { s.active.reset();s.waiting.clear();s.poisoned=true; }
  std::map<int,Slot> slots_;
};
int main() {
  Scheduler q;
  assert(q.enqueue(1,{Source::Kernel,101}));
  assert(q.enqueue(1,{Source::UhidOutput,0}));
  assert(q.enqueue(1,{Source::Hal,0}));
  assert(q.enqueue(1,{Source::Kernel,102}));
  assert(!q.enqueue(1,{Source::Kernel,103})); // bounded pending
  assert(q.waiting(1)==3);
  assert(q.enqueue(2,{Source::Hal,0})); // independent
  assert(!q.enqueue(3,{Source::Hal,123})); // invalid provenance
  assert(q.finish(1));
  assert(q.poisoned(1) && q.waiting(1)==0 && !q.has_active(1));
  assert(!q.enqueue(1,{Source::Kernel,104})); // cannot auto-reuse handle
  assert(!q.finish(1)); // duplicate
  q.timeout_or_disconnect(2);
  assert(!q.finish(2) && !q.enqueue(2,{Source::Kernel,105}));
  std::cout<<"bounded multi-producer scheduler host assertions PASS\\n";
}
