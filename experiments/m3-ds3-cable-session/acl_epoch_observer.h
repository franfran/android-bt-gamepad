// RetroBox host-testable, passive ACL lifetime correlation; NEVER an auth grant.
#ifndef RETROBOX_ACL_EPOCH_OBSERVER_H_
#define RETROBOX_ACL_EPOCH_OBSERVER_H_

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <optional>

namespace retrobox {
struct AclObservationTicket {
  uint16_t hci_handle = 0;
  uintptr_t lcb_identity = 0;  // Address used only within this process.
  uint64_t generation = 0;
  bool operator==(const AclObservationTicket& o) const {
    return hci_handle == o.hci_handle && lcb_identity == o.lcb_identity &&
           generation == o.generation;
  }
};

class AclEpochObserver {
 public:
  static constexpr size_t kSlots = 32;
  // A bounded, non-authorizing debug table; no peer addresses or key material.
  explicit AclEpochObserver(size_t capacity = kSlots)
      : capacity_(capacity <= kSlots ? capacity : kSlots) {}

  std::optional<AclObservationTicket> Connected(uint16_t handle,
                                                  uintptr_t lcb_identity) {
    if (handle == 0xffff || !lcb_identity ||
        next_generation_ == std::numeric_limits<uint64_t>::max())
      return std::nullopt;
    // A handle or LCB slot is reusable. Retire prior observations first.
    for (size_t i = 0; i < capacity_; ++i) {
      auto& slot = slots_[i];
      if (slot.used && (slot.ticket.hci_handle == handle ||
                        slot.ticket.lcb_identity == lcb_identity))
        slot.used = false;
    }
    for (size_t i = 0; i < capacity_; ++i) {
      auto& slot = slots_[i];
      if (!slot.used) {
        slot.ticket = {handle, lcb_identity, ++next_generation_};
        slot.used = true;
        return slot.ticket;
      }
    }
    // Capacity exhausted: no guessed token and no unrelated eviction.
    return std::nullopt;
  }

  std::optional<AclObservationTicket> Current(uint16_t handle,
                                                uintptr_t lcb_identity) const {
    for (size_t i = 0; i < capacity_; ++i) {
      const auto& slot = slots_[i];
      if (slot.used && slot.ticket.hci_handle == handle &&
          slot.ticket.lcb_identity == lcb_identity)
        return slot.ticket;
    }
    return std::nullopt;
  }

  bool Retire(AclObservationTicket ticket) {
    for (size_t i = 0; i < capacity_; ++i) {
      auto& slot = slots_[i];
      if (slot.used && slot.ticket == ticket) {
        slot.used = false;
        return true;
      }
    }
    return false;
  }

  void Clear() {
    for (size_t i = 0; i < capacity_; ++i) slots_[i].used = false;
    // Generation deliberately persists to prevent reuse on service reinit.
  }

 private:
  struct Slot {
    AclObservationTicket ticket;
    bool used = false;
  };
  std::array<Slot, kSlots> slots_{};
  size_t capacity_;
  uint64_t next_generation_ = 0;
};
}  // namespace retrobox
#endif  // RETROBOX_ACL_EPOCH_OBSERVER_H_
