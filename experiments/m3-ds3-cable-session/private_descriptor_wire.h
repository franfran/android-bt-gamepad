// Host-only byte serialization of a hypothetical private BTA/BTIF HID event.
// Not a registered event or an ABI patch; no raw pointers cross the byte copy.
#ifndef RETROBOX_PRIVATE_DESCRIPTOR_WIRE_H_
#define RETROBOX_PRIVATE_DESCRIPTOR_WIRE_H_
#include "private_descriptor_transport.h"
#include <cstddef>
#include <cstdint>
#include <deque>
#include <limits>
#include <optional>
#include <vector>

namespace retrobox {

struct WireDescriptor {
  DescriptorTicket ticket;
  std::vector<uint8_t> descriptor;
};

class PrivateDescriptorWire {
 public:
  // 4 magic, 1 version, 1 HID handle, 8 generation LE, 2 descriptor length LE.
  static constexpr size_t kHeaderLength = 16;
  static constexpr size_t kMaxFixtureDescriptor = 4096; // NOT DS3 production limit.

  static std::optional<std::vector<uint8_t>> Encode(DescriptorTicket t,
      const uint8_t* bytes, size_t length) {
    if (t.generation == 0 || !bytes || length == 0 ||
        length > kMaxFixtureDescriptor || length > UINT16_MAX) return std::nullopt;
    std::vector<uint8_t> blob(kHeaderLength + length, 0);
    blob[0] = 'R'; blob[1] = 'B'; blob[2] = 'H'; blob[3] = 'D';
    blob[4] = 1; blob[5] = t.handle;
    for (size_t i = 0; i < 8; ++i) blob[6 + i] = static_cast<uint8_t>(t.generation >> (8 * i));
    blob[14] = static_cast<uint8_t>(length);
    blob[15] = static_cast<uint8_t>(length >> 8);
    for (size_t i = 0; i < length; ++i) blob[kHeaderLength + i] = bytes[i];
    return blob;
  }

  static std::optional<WireDescriptor> Decode(const std::vector<uint8_t>& blob) {
    if (blob.size() < kHeaderLength || blob[0] != 'R' || blob[1] != 'B' ||
        blob[2] != 'H' || blob[3] != 'D' || blob[4] != 1) return std::nullopt;
    uint64_t generation = 0;
    for (size_t i = 0; i < 8; ++i)
      generation |= uint64_t{blob[6 + i]} << (8 * i);
    const size_t len = static_cast<size_t>(blob[14]) |
                       (static_cast<size_t>(blob[15]) << 8);
    if (generation == 0 || len == 0 || len > kMaxFixtureDescriptor ||
        blob.size() != kHeaderLength + len) return std::nullopt;
    return WireDescriptor{{blob[5], generation},
                          std::vector<uint8_t>(blob.begin() + kHeaderLength, blob.end())};
  }
};

class PrivateWireQueue {
 public:
  explicit PrivateWireQueue(size_t max_messages = 8) : max_messages_(max_messages) {}

  bool Post(DescriptorTicket ticket, const uint8_t* bytes, size_t length,
            bool simulate_successful_scheduler_post = true) {
    if (queue_.size() >= max_messages_ || !simulate_successful_scheduler_post) return false;
    auto envelope = PrivateDescriptorWire::Encode(ticket, bytes, length);
    if (!envelope) return false;
    queue_.push_back(std::move(*envelope));
    return true;
  }

  template <typename Consumer>
  bool DispatchOne(Consumer& consumer) {
    if (queue_.empty()) return false;
    auto blob = std::move(queue_.front());
    queue_.pop_front();
    auto packet = PrivateDescriptorWire::Decode(blob);
    if (!packet) return false;
    return consumer(packet->ticket, packet->descriptor);
  }

  void CancelAll() { queue_.clear(); }
  size_t Pending() const { return queue_.size(); }
 private:
  size_t max_messages_;
  std::deque<std::vector<uint8_t>> queue_;
};
} // namespace retrobox
#endif // RETROBOX_PRIVATE_DESCRIPTOR_WIRE_H_
