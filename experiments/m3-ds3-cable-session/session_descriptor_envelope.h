// Host-only research model. NOT a Bluetooth security or Android integration.
#ifndef RETROBOX_SESSION_DESCRIPTOR_ENVELOPE_H_
#define RETROBOX_SESSION_DESCRIPTOR_ENVELOPE_H_

#include <cstddef>
#include <cstdint>
#include <optional>
#include <unordered_map>
#include <vector>

namespace retrobox {

struct Ticket {
  uint8_t hid_handle;
  uint64_t generation;
  bool operator==(const Ticket& other) const {
    return hid_handle == other.hid_handle && generation == other.generation;
  }
};

struct OwnedDescriptor {
  Ticket ticket;
  std::vector<uint8_t> bytes;
};

class DescriptorGate {
 public:
  // A test fixture ceiling, NOT a validated DS3 Bluetooth descriptor limit.
  explicit DescriptorGate(size_t max_fixture_length = 4096);
  Ticket Open(uint8_t hid_handle, bool native_policy_passed);
  bool ReceiveDescriptor(Ticket ticket, const uint8_t* bytes, size_t length,
                         bool fixture_gamepad_valid);
  bool JavaDecision(Ticket ticket, bool allowed);
  std::optional<OwnedDescriptor> ReleaseUhidCreate(Ticket ticket);
  bool AllowUhidInput(Ticket ticket, bool kernel_ready,
                      bool fixture_report_valid);
  bool Close(Ticket ticket);
  size_t ActiveCandidates() const;

 private:
  struct Candidate {
    Ticket ticket;
    bool native_policy_passed = false;
    bool java_allowed = false;
    bool uhid_created = false;
    std::optional<std::vector<uint8_t>> owned_descriptor;
  };

  Candidate* Current(Ticket ticket);
  uint64_t next_generation_ = 0;
  size_t max_fixture_length_;
  std::unordered_map<uint8_t, Candidate> candidates_;
};

}  // namespace retrobox
#endif  // RETROBOX_SESSION_DESCRIPTOR_ENVELOPE_H_
