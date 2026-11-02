// Host-only model. Never infer an authenticated peer from an open UHID fd.
#ifndef RETROBOX_PROVISIONAL_UHID_GATE_H_
#define RETROBOX_PROVISIONAL_UHID_GATE_H_
#include <array>
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <mutex>
#include <optional>
#include <utility>

namespace retrobox {
struct OpenToken {
  int fd;
  uint8_t hid_handle;
  uint64_t open_generation;
  bool operator==(const OpenToken& rhs) const {
    return fd == rhs.fd && hid_handle == rhs.hid_handle &&
           open_generation == rhs.open_generation;
  }
};
enum class UhidOp { kCreate, kInput, kDestroy, kOther };
enum class Classification { kProvisional, kCandidate, kStandard };
// All evidence here is symbolic. The H618 source has not supplied trusted
// ACL/HCI/bond/Java provenance to this model; no peer authentication is added.
struct StandardEvidence {
  bool native_auth_completed;
  bool acl_session_matches;
  bool java_bonded;
  bool java_policy_allowed;
  bool descriptor_validated;
};

class ProvisionalUhidGate {
 public:
  static constexpr size_t kCapacity = 8;

  // Must be called immediately after every successful /dev/uhid open, BEFORE
  // launching a poll thread or returning to BTA. Never trust an old MAC here.
  std::optional<OpenToken> Open(int fd, uint8_t handle) {
    std::lock_guard<std::mutex> lock(mu_);
    if (fd < 0 || handle == 0xff || next_ == UINT64_MAX) return std::nullopt;
    for (const Slot& slot : slots_)
      if (slot.state != State::kFree &&
          (slot.token.fd == fd || slot.token.hid_handle == handle))
        return std::nullopt;
    for (Slot& slot : slots_) {
      if (slot.state == State::kFree) {
        slot.token = {fd, handle, ++next_};
        slot.state = State::kProvisional;
        return slot.token;
      }
    }
    return std::nullopt;  // caller must immediately abort and close opened fd
  }

  bool MarkCandidate(OpenToken token) {
    std::lock_guard<std::mutex> lock(mu_);
    Slot* slot = Find(token);
    if (!slot || slot->state != State::kProvisional) return false;
    slot->state = State::kCandidate;  // no candidate promotion API exists
    return true;
  }

  // Only the normal authenticated/bonded HID path can be released. A caller
  // must substantiate all evidence from trusted Native + Java session state.
  bool PermitStandard(OpenToken token, const StandardEvidence& evidence) {
    std::lock_guard<std::mutex> lock(mu_);
    Slot* slot = Find(token);
    if (!slot || slot->state != State::kProvisional ||
        !evidence.native_auth_completed || !evidence.acl_session_matches ||
        !evidence.java_bonded || !evidence.java_policy_allowed ||
        !evidence.descriptor_validated) return false;
    slot->state = State::kStandard;
    return true;
  }

  bool Quarantine(OpenToken token) {
    std::lock_guard<std::mutex> lock(mu_);
    Slot* slot = Find(token);
    if (!slot || slot->state == State::kQuarantined) return false;
    slot->state = State::kQuarantined;
    return true;
  }

  template <typename WriteFn>
  int WithWrite(int fd, UhidOp op, WriteFn&& actual_write) {
    std::lock_guard<std::mutex> lock(mu_);
    if (op == UhidOp::kCreate || op == UhidOp::kInput) {
      State state = State::kFree;
      for (const Slot& slot : slots_)
        if (slot.state != State::kFree && slot.token.fd == fd) {
          state = slot.state;
          break;
        }
      // Unlike the v2 candidate-only fence, UNKNOWN is also denied.
      if (state != State::kStandard) return -EACCES;
    }
    return std::forward<WriteFn>(actual_write)();
  }

  // Close owns the fd: no deregistration before the kernel close callback.
  // Failed close keeps a tombstone; stale close cannot release successor fd.
  template <typename CloseFn>
  bool Close(OpenToken token, CloseFn&& actual_close) {
    std::lock_guard<std::mutex> lock(mu_);
    Slot* slot = Find(token);
    if (!slot) return false;
    slot->state = State::kQuarantined;
    if (!std::forward<CloseFn>(actual_close)(token.fd)) return false;
    slot->state = State::kFree;
    return true;
  }

  size_t Count() const {
    std::lock_guard<std::mutex> lock(mu_);
    size_t n = 0;
    for (const Slot& slot : slots_) n += slot.state != State::kFree;
    return n;
  }
 private:
  enum class State { kFree, kProvisional, kCandidate, kStandard, kQuarantined };
  struct Slot { OpenToken token{}; State state = State::kFree; };
  Slot* Find(OpenToken token) {
    for (Slot& slot : slots_)
      if (slot.state != State::kFree && slot.token == token) return &slot;
    return nullptr;
  }
  mutable std::mutex mu_;
  std::array<Slot, kCapacity> slots_{};
  uint64_t next_ = 0;
};
} // namespace retrobox
#endif
