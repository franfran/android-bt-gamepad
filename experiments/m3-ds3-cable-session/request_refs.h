// Host model only: opaque BTM callback references, never reused in one process.
#ifndef RETROBOX_DS3_REQUEST_REFS_H_
#define RETROBOX_DS3_REQUEST_REFS_H_
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>

namespace retrobox {
struct RequestIdentity {
  uint16_t hci_handle;
  uintptr_t lcb;
  uintptr_t ccb;
  uint64_t epoch;
  uint16_t psm;
  bool operator==(const RequestIdentity& rhs) const {
    return hci_handle == rhs.hci_handle && lcb == rhs.lcb &&
           ccb == rhs.ccb && epoch == rhs.epoch && psm == rhs.psm;
  }
};
enum class SecurityEvent { kDelay, kSuccess, kFailure };
struct CallbackOutcome {
  bool forward;
  bool terminal;
};

class RequestRefPool {
 public:
  static constexpr size_t kCapacity = 64;
  // Pointers are opaque identity values. Entries are never recycled until
  // process exit, preventing ABA even when CCB/LCB/HCI handle are reused.
  void* Begin(const RequestIdentity& id) {
    if ((id.psm != 0x11 && id.psm != 0x13) || id.hci_handle == 0xffff ||
        !id.epoch || !id.lcb || !id.ccb) return nullptr;
    if (next_ == kCapacity) return nullptr;
    Slot& s = slots_[next_++];
    s.id = id;
    s.state = State::kActive;
    return &s;
  }

  CallbackOutcome OnCallback(void* opaque, const RequestIdentity& live,
                             SecurityEvent event) {
    Slot* slot = Find(opaque);
    if (!slot || slot->state != State::kActive) return {false, false};
    if (!(slot->id == live)) {
      slot->state = State::kRetired;
      return {false, false};
    }
    if (event == SecurityEvent::kDelay) return {true, false};
    slot->state = State::kCompleted;
    return {true, true};
  }

  bool Retire(void* opaque) {
    Slot* slot = Find(opaque);
    if (!slot || slot->state != State::kActive) return false;
    slot->state = State::kRetired;
    return true;
  }
  size_t RetireCcb(uintptr_t ccb) {
    size_t result = 0;
    for (size_t i = 0; i < next_; ++i) {
      Slot& s = slots_[i];
      if (s.state == State::kActive && s.id.ccb == ccb) {
        s.state = State::kRetired;
        ++result;
      }
    }
    return result;
  }
  size_t RetireLcb(uintptr_t lcb) {
    size_t result = 0;
    for (size_t i = 0; i < next_; ++i) {
      Slot& s = slots_[i];
      if (s.state == State::kActive && s.id.lcb == lcb) {
        s.state = State::kRetired;
        ++result;
      }
    }
    return result;
  }
  size_t Issued() const { return next_; }

 private:
  enum class State { kUnused, kActive, kRetired, kCompleted };
  struct Slot {
    RequestIdentity id{};
    State state = State::kUnused;
  };
  Slot* Find(void* opaque) {
    // Compare pointer values; never dereference untrusted BTM ref_data.
    for (size_t i = 0; i < next_; ++i)
      if (opaque == &slots_[i]) return &slots_[i];
    return nullptr;
  }
  std::array<Slot, kCapacity> slots_{};
  size_t next_ = 0;
};
} // namespace retrobox
#endif
