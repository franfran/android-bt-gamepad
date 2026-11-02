// Host-only candidate lifecycle gate; no Bluetooth authentication grant.
#ifndef RETROBOX_DS3_CANDIDATE_LIFECYCLE_GATE_H_
#define RETROBOX_DS3_CANDIDATE_LIFECYCLE_GATE_H_

#include <array>
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <mutex>
#include <utility>

namespace retrobox {
struct CandidateLifecycleTicket {
  int fd;
  uint8_t hid_handle;
  uint64_t acl_epoch;
  uint64_t request_id;
  bool operator==(const CandidateLifecycleTicket& other) const {
    return fd == other.fd && hid_handle == other.hid_handle &&
           acl_epoch == other.acl_epoch && request_id == other.request_id;
  }
};

enum class UhidEventKind { kCreate, kInput, kDestroy, kOther };

// All methods are serialized with WithKernelWrite, including its actual write.
// This is a deny-only fence, NOT a trusted DS3 classifier or approval gate.
class CandidateLifecycleGate {
 public:
  static constexpr size_t kCapacity = 8;

  // A verified Native caller must classify BEFORE any UHID event. On failure,
  // caller must close/abort the entire candidate (never fall through to stock).
  bool RegisterCandidate(CandidateLifecycleTicket ticket) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (ticket.fd < 0 || ticket.hid_handle == 0xff ||
        !ticket.acl_epoch || !ticket.request_id) return false;
    for (const Slot& slot : slots_) {
      if (slot.state != State::kFree &&
          (slot.ticket.fd == ticket.fd ||
           slot.ticket.hid_handle == ticket.hid_handle)) return false;
    }
    for (Slot& slot : slots_) {
      if (slot.state == State::kFree) {
        slot.ticket = ticket;
        slot.state = State::kPending;
        return true;
      }
    }
    return false;
  }

  // Disconnect/Java veto keeps fd blocked until actual close. Exact ticket only.
  bool Quarantine(CandidateLifecycleTicket ticket) {
    std::lock_guard<std::mutex> lock(mutex_);
    for (Slot& slot : slots_) {
      if (slot.state == State::kPending && slot.ticket == ticket) {
        slot.state = State::kQuarantined;
        return true;
      }
    }
    return false;
  }

  // The close() action is intentionally inside the same lock as kernel writes.
  // Requires proof of real close success from the caller (not merely a Boolean
  // Java response). Failed close leaves the fd quarantined.
  template <typename CloseFn>
  bool CloseQuarantined(CandidateLifecycleTicket ticket, CloseFn&& close_fd) {
    std::lock_guard<std::mutex> lock(mutex_);
    for (Slot& slot : slots_) {
      if (slot.state == State::kQuarantined && slot.ticket == ticket) {
        if (!std::forward<CloseFn>(close_fd)(ticket.fd)) return false;
        slot.state = State::kFree;
        return true;
      }
    }
    return false;
  }

  // A single critical section covers candidate lookup AND the final write.
  // Without this, disconnect/revoke after IsBlocked but before write is a TOCTOU.
  template <typename WriteFn>
  int WithKernelWrite(int fd, UhidEventKind event, WriteFn&& write_event) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (event == UhidEventKind::kCreate || event == UhidEventKind::kInput) {
      for (const Slot& slot : slots_) {
        if (slot.state != State::kFree && slot.ticket.fd == fd)
          return -EACCES;
      }
    }
    return std::forward<WriteFn>(write_event)();
  }

  bool IsBlocked(int fd) const { // Early hint only; final write MUST recheck.
    std::lock_guard<std::mutex> lock(mutex_);
    for (const Slot& slot : slots_)
      if (slot.state != State::kFree && slot.ticket.fd == fd) return true;
    return false;
  }

  size_t Held() const {
    std::lock_guard<std::mutex> lock(mutex_);
    size_t result = 0;
    for (const Slot& slot : slots_) result += slot.state != State::kFree;
    return result;
  }

 private:
  enum class State : uint8_t { kFree, kPending, kQuarantined };
  struct Slot { CandidateLifecycleTicket ticket{}; State state = State::kFree; };
  mutable std::mutex mutex_;
  std::array<Slot, kCapacity> slots_{};
};
}  // namespace retrobox
#endif  // RETROBOX_DS3_CANDIDATE_LIFECYCLE_GATE_H_
