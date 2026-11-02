// Offline research model: private BTA-to-BTIF descriptor message ownership.
// NOT a working Fluoride event or approval of nonbonded Bluetooth traffic.
#ifndef RETROBOX_PRIVATE_DESCRIPTOR_TRANSPORT_H_
#define RETROBOX_PRIVATE_DESCRIPTOR_TRANSPORT_H_
#include <cstddef>
#include <cstdint>
#include <deque>
#include <vector>
#include <algorithm>

namespace retrobox {

struct DescriptorTicket {
  uint8_t handle;
  uint64_t generation;
  bool operator==(const DescriptorTicket& o) const {
    return handle == o.handle && generation == o.generation;
  }
};

// Private envelope is an OWNED value; never an exposed BTA callback struct.
struct DescriptorEnvelope {
  DescriptorTicket ticket;
  bool fixture_gamepad_valid;
  std::vector<uint8_t> descriptor;
};

class PrivateDescriptorTransport {
 public:
  explicit PrivateDescriptorTransport(size_t max_descriptor_length = 4096,
                                     size_t max_pending_messages = 8)
      : max_descriptor_length_(max_descriptor_length),
        max_pending_messages_(max_pending_messages) {}

  bool Submit(DescriptorTicket ticket, const uint8_t* bytes, size_t length,
              bool fixture_gamepad_valid) {
    if (!bytes || length == 0 || length > max_descriptor_length_ ||
        queue_.size() >= max_pending_messages_) return false;
    if (std::any_of(queue_.begin(), queue_.end(), [ticket](const DescriptorEnvelope& e) {
      return e.ticket == ticket;
    })) return false;
    queue_.push_back(DescriptorEnvelope{ticket, fixture_gamepad_valid,
                                        std::vector<uint8_t>(bytes, bytes + length)});
    return true;
  }

  template <typename Consumer>
  bool DispatchOne(Consumer& consumer) {
    if (queue_.empty()) return false;
    DescriptorEnvelope event = std::move(queue_.front());
    queue_.pop_front();
    // Consumer verifies the epoch and Native policy. Dropping event destroys
    // its descriptor buffer even after a denial.
    return consumer(event.ticket, event.descriptor, event.fixture_gamepad_valid);
  }

  size_t Cancel(DescriptorTicket ticket) {
    const size_t before = queue_.size();
    queue_.erase(std::remove_if(queue_.begin(), queue_.end(), [ticket](const DescriptorEnvelope& e) {
                   return e.ticket == ticket;
                 }), queue_.end());
    return before - queue_.size();
  }

  void CancelAll() { queue_.clear(); }
  size_t Pending() const { return queue_.size(); }

 private:
  size_t max_descriptor_length_;
  size_t max_pending_messages_;
  std::deque<DescriptorEnvelope> queue_;
};

}  // namespace retrobox
#endif  // RETROBOX_PRIVATE_DESCRIPTOR_TRANSPORT_H_
