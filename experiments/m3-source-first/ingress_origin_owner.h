// S7 host-only ingress-origin admission. No Bluetooth, UHID, or Android API calls.
#pragma once
#include <cstdint>
#include <map>
#include <optional>
enum class IngressOrigin { KernelSet, KernelOutputFeature, JavaHal };
enum class Admission { Accepted, Busy, Quarantined, InvalidOrigin };
struct IngressTicket { IngressOrigin origin; uint32_t kernel_id; uint64_t generation; };
class IngressOwner {
 public:
  Admission enter(uint16_t handle, IngressTicket ticket) {
    auto& s = state_[handle];
    if (s.quarantined) return Admission::Quarantined;
    if (ticket.origin != IngressOrigin::KernelSet && ticket.kernel_id != 0)
      return Admission::InvalidOrigin;
    if (s.active.has_value()) return Admission::Busy;
    s.active = ticket;
    return Admission::Accepted;
  }
  std::optional<IngressTicket> local_failure(uint16_t handle, uint64_t generation) {
    auto it=state_.find(handle);
    if (it==state_.end() || !it->second.active ||
        it->second.active->generation != generation) return std::nullopt;
    auto ticket=*it->second.active;
    it->second.active.reset();
    it->second.quarantined=true;  // cannot assume no queued stale callback
    return ticket;  // diagnostic, NOT a kernel reply
  }
  void disconnect(uint16_t handle) {
    auto& s=state_[handle]; s.active.reset();s.quarantined=true;
  }
 private:
  struct State { bool quarantined=false; std::optional<IngressTicket> active; };
  std::map<uint16_t,State> state_;
};
