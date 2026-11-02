// Offline candidate-only UHID deny fence. No source of trusted identity here.
#ifndef RETROBOX_CANDIDATE_UHID_FENCE_H_
#define RETROBOX_CANDIDATE_UHID_FENCE_H_

#include <array>
#include <cstddef>
#include <cstdint>
#include <mutex>
#include <optional>

namespace retrobox {
struct FenceTicket {
  int fd;
  uint8_t handle;
  uint64_t acl_epoch;
  uint64_t request_id;
  bool operator==(const FenceTicket& rhs) const {
    return fd == rhs.fd && handle == rhs.handle &&
           acl_epoch == rhs.acl_epoch && request_id == rhs.request_id;
  }
};

class CandidateUhidFence {
 public:
  static constexpr size_t kCapacity = 8;

  // Caller MUST already have trusted Native candidate classification.
  // Failure is NOT permission to proceed with ordinary HID.
  bool RegisterCandidate(FenceTicket ticket) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (ticket.fd < 0 || ticket.handle == 0xff ||
        !ticket.acl_epoch || !ticket.request_id) return false;
    for (const auto& slot : slots_) {
      if (slot.active && (slot.ticket.fd == ticket.fd ||
                          slot.ticket.handle == ticket.handle))
        return false;
    }
    for (auto& slot : slots_) {
      if (!slot.active) {
        slot.ticket = ticket;
        slot.active = true;
        return true;
      }
    }
    return false;  // must reject candidate if registry is exhausted
  }

  // Return false for BOTH CREATE and INPUT whenever candidate is pending.
  // There is deliberately no approval operation in this research class.
  bool AllowKernelEvent(int fd, bool is_create_or_input) const {
    if (!is_create_or_input) return true;
    std::lock_guard<std::mutex> lock(mutex_);
    for (const auto& slot : slots_) {
      if (slot.active && slot.ticket.fd == fd) return false;
    }
    return true;  // ordinary, unclassified, existing bonded HID path
  }

  bool Revoke(FenceTicket ticket) {
    std::lock_guard<std::mutex> lock(mutex_);
    for (auto& slot : slots_) {
      if (slot.active && slot.ticket == ticket) {
        slot.active = false;
        return true;
      }
    }
    return false;  // stale disconnect cannot clear a replacement ticket
  }

  size_t Pending() const {
    std::lock_guard<std::mutex> lock(mutex_);
    size_t result = 0;
    for (const auto& slot : slots_) result += slot.active;
    return result;
  }

 private:
  struct Slot {
    FenceTicket ticket{};
    bool active = false;
  };
  mutable std::mutex mutex_;
  std::array<Slot, kCapacity> slots_{};
};
}  // namespace retrobox
#endif  // RETROBOX_CANDIDATE_UHID_FENCE_H_
