// Host-only model of a dedicated checked BTA->BTIF private JNI task.
// No actual Fluoride/Android scheduling, Bluetooth, or security relaxation.
#ifndef RETROBOX_PRIVATE_CHECKED_DISPATCH_H_
#define RETROBOX_PRIVATE_CHECKED_DISPATCH_H_
#include "private_descriptor_wire.h"
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <memory>
#include <utility>
#include <vector>

namespace retrobox {

struct DispatchLifetime {
  size_t constructed = 0;
  size_t destroyed = 0;
};

struct PrivateJniTask {
  PrivateJniTask(std::vector<uint8_t> owned_bytes, DispatchLifetime* lifetimes)
      : payload(std::move(owned_bytes)), counter(lifetimes) {
    if (counter) ++counter->constructed;
  }
  PrivateJniTask(const PrivateJniTask&) = delete;
  PrivateJniTask& operator=(const PrivateJniTask&) = delete;
  ~PrivateJniTask() { if (counter) ++counter->destroyed; }
  std::vector<uint8_t> payload;  // Internal, owned task; NOT memcpy'able event.
  DispatchLifetime* counter;    // Test instrumentation ONLY.
};

class CheckedPrivateJniDispatcher {
 public:
  explicit CheckedPrivateJniDispatcher(size_t max_queued = 8)
      : max_queued_(max_queued) {}

  // Model an explicit, checkable JNI scheduler status. On failure, task local
  // ownership is destroyed immediately; stock btif_transfer_context doesn't
  // provide this guarantee and must NOT be used as-is for a private envelope.
  bool Submit(DescriptorTicket ticket, const uint8_t* descriptor, size_t length,
              bool scheduler_accepts, DispatchLifetime* stats = nullptr) {
    auto bytes = PrivateDescriptorWire::Encode(ticket, descriptor, length);
    if (!bytes) return false;
    auto task = std::make_unique<PrivateJniTask>(std::move(*bytes), stats);
    if (!scheduler_accepts || queued_.size() >= max_queued_) return false;
    queued_.push_back(std::move(task));
    return true;
  }

  template <typename Fn>
  bool RunOne(Fn&& consume) {
    if (queued_.empty()) return false;
    auto event = std::move(queued_.front());
    queued_.pop_front();
    const auto decoded = PrivateDescriptorWire::Decode(event->payload);
    if (!decoded) return false;  // event destroyed by RAII on every path
    return consume(decoded->ticket, decoded->descriptor);
  }

  size_t Cancel(DescriptorTicket ticket) {
    const size_t before = queued_.size();
    queued_.erase(std::remove_if(queued_.begin(), queued_.end(), [ticket](const auto& e) {
      const auto decoded = PrivateDescriptorWire::Decode(e->payload);
      return decoded && decoded->ticket == ticket;
    }), queued_.end());
    return before - queued_.size();
  }

  void Shutdown() { queued_.clear(); }
  size_t Pending() const { return queued_.size(); }

 private:
  size_t max_queued_;
  std::deque<std::unique_ptr<PrivateJniTask>> queued_;
};
} // namespace retrobox
#endif // RETROBOX_PRIVATE_CHECKED_DISPATCH_H_
